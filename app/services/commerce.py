from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartLine, CartRead
from app.schemas.product import ProductRead


def get_cart(db: Session, user_id: int) -> CartRead:
    rows = db.execute(
        select(CartItem, Product)
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    )
    lines: list[CartLine] = []
    total = Decimal("0.00")
    for item, product in rows:
        line_total = product.price * item.quantity
        total += line_total
        lines.append(
            CartLine(
                product=ProductRead.model_validate(product),
                quantity=item.quantity,
                line_total=line_total,
            )
        )
    return CartRead(items=lines, total_amount=total)


def add_cart_item(
    db: Session, user_id: int, product_id: int, quantity: int
) -> CartRead:
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user_id, CartItem.product_id == product_id
        )
    )
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > product.stock:
        raise HTTPException(
            status_code=409, detail="Requested quantity exceeds available stock"
        )
    if item is None:
        db.add(CartItem(user_id=user_id, product_id=product_id, quantity=quantity))
    else:
        item.quantity = new_quantity
    db.commit()
    return get_cart(db, user_id)


def update_cart_item(
    db: Session, user_id: int, product_id: int, quantity: int
) -> CartRead:
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if quantity > product.stock:
        raise HTTPException(
            status_code=409, detail="Requested quantity exceeds available stock"
        )
    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_cart_item(db: Session, user_id: int, product_id: int) -> None:
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()


def checkout(db: Session, user_id: int) -> Order:
    cart_rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(Product.id)
            .with_for_update()
        )
    )
    if not cart_rows:
        raise HTTPException(
            status_code=409, detail="Cannot create an order from an empty cart"
        )

    total = sum(
        (product.price * cart_item.quantity for cart_item, product in cart_rows),
        start=Decimal("0.00"),
    )
    order = Order(user_id=user_id, total_amount=total)
    db.add(order)
    db.flush()

    for cart_item, product in cart_rows:
        result = db.execute(
            update(Product)
            .where(Product.id == product.id, Product.stock >= cart_item.quantity)
            .values(stock=Product.stock - cart_item.quantity)
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for product {product.id}",
            )
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=cart_item.quantity,
                unit_price=product.price,
            )
        )
        db.delete(cart_item)

    order_id = order.id
    db.commit()
    completed_order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if completed_order is None:
        raise RuntimeError("Committed order could not be loaded")
    return completed_order
