from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderRead
from app.services.commerce import checkout

router = APIRouter(prefix="/orders", tags=["Buyurtmalar"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Order:
    """Savatni tekshirib, qoldiqni kamaytirish bilan bir tranzaksiyada buyurtma beradi."""
    return checkout(db, user.id)


@router.get("", response_model=list[OrderRead])
def list_orders(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Order]:
    """Faqat token egasining buyurtmalarini sahifalab qaytaradi."""
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(orders)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Order:
    """Buyurtma boshqa foydalanuvchiga tegishli bo‘lsa, uni mavjud emas deb qaytaradi."""
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == user.id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    return order
