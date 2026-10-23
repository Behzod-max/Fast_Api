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
    """Savat qatorlari va summasini serverda hisoblaydi."""
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
    """Foydalanuvchi savatini qulflab, miqdorni ombordagi qoldiq bilan solishtiradi."""
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user_id, CartItem.product_id == product_id
        )
    )
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > product.stock:
        raise HTTPException(
            status_code=409,
            detail="So‘ralgan miqdor ombordagi qoldiqdan oshib ketdi",
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
    """Savat qatorini qulflab, miqdorni zaxiradan oshirmasdan yangilaydi."""
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Savatda bunday mahsulot yo‘q")
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    if quantity > product.stock:
        raise HTTPException(
            status_code=409,
            detail="So‘ralgan miqdor ombordagi qoldiqdan oshib ketdi",
        )
    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_cart_item(db: Session, user_id: int, product_id: int) -> None:
    """Savat qatorini egasini tekshirib o‘chiradi."""
    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id, CartItem.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Savatda bunday mahsulot yo‘q")
    db.delete(item)
    db.commit()


def checkout(db: Session, user_id: int) -> Order:
    """Buyurtma, narx nusxasi, zaxira va savatni bitta tranzaksiyada boshqaradi."""
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
            status_code=409, detail="Bo‘sh savatdan buyurtma yaratib bo‘lmaydi"
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
                detail=f"{product.id}-mahsulot uchun omborda yetarli qoldiq yo‘q",
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
        raise RuntimeError("Saqlangan buyurtmani qayta o‘qib bo‘lmadi")
    return completed_order
