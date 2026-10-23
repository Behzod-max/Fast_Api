from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.order import Buyurtma
from app.models.user import Foydalanuvchi
from app.schemas.order import BuyurtmaJavobi
from app.services.commerce import checkout

router = APIRouter(prefix="/orders", tags=["Buyurtmalar"])


@router.post("", response_model=BuyurtmaJavobi, status_code=status.HTTP_201_CREATED)
def create_order(
    db: Session = Depends(get_db), user: Foydalanuvchi = Depends(get_current_user)
) -> Buyurtma:
    """Savatni tekshirib, qoldiqni kamaytirish bilan bir tranzaksiyada buyurtma beradi."""
    return checkout(db, user.id)


@router.get("", response_model=list[BuyurtmaJavobi])
def list_orders(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Foydalanuvchi = Depends(get_current_user),
) -> list[Buyurtma]:
    """Faqat token egasining buyurtmalarini sahifalab qaytaradi."""
    orders = db.scalars(
        select(Buyurtma)
        .options(selectinload(Buyurtma.items))
        .where(Buyurtma.user_id == user.id)
        .order_by(Buyurtma.created_at.desc(), Buyurtma.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(orders)


@router.get("/{order_id}", response_model=BuyurtmaJavobi)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: Foydalanuvchi = Depends(get_current_user),
) -> Buyurtma:
    """Buyurtma boshqa foydalanuvchiga tegishli bo‘lsa, uni mavjud emas deb qaytaradi."""
    order = db.scalar(
        select(Buyurtma)
        .options(selectinload(Buyurtma.items))
        .where(Buyurtma.id == order_id, Buyurtma.user_id == user.id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    return order
