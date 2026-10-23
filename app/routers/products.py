from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.cart_item import CartItem
from app.models.category import Category
from app.models.order import OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductSalesRead,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Product:
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = Query(default=None, gt=0),
    min_price: Decimal | None = Query(default=None, gt=0),
    max_price: Decimal | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[Product]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price")
    query = select(Product)
    if search:
        query = query.where(Product.name.ilike(f"%{search.strip()}%"))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    return list(db.scalars(query.order_by(Product.id).offset(offset).limit(limit)))


@router.get("/best-sellers", response_model=list[ProductSalesRead])
def best_sellers(
    limit: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db)
) -> list[ProductSalesRead]:
    rows = db.execute(
        select(Product, func.sum(OrderItem.quantity).label("sold_units"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc(), Product.id)
        .limit(limit)
    )
    return [
        ProductSalesRead.model_validate(
            {
                **ProductRead.model_validate(product).model_dump(),
                "sold_units": sold_units,
            }
        )
        for product, sold_units in rows
    ]


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and db.get(Category, changes["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in changes.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if (
        db.scalar(
            select(OrderItem.id).where(OrderItem.product_id == product_id).limit(1)
        )
        is not None
    ):
        raise HTTPException(
            status_code=409, detail="Product has order history and cannot be deleted"
        )
    db.query(CartItem).filter(CartItem.product_id == product_id).delete(
        synchronize_session=False
    )
    db.delete(product)
    db.commit()
