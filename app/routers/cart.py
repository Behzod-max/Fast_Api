from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import Foydalanuvchi
from app.schemas.cart import (
    SavatJavobi,
    SavatMahsulotiYangilash,
    SavatMahsulotiYaratish,
)
from app.services.commerce import (
    add_cart_item as add_cart_item_service,
)
from app.services.commerce import (
    get_cart,
)
from app.services.commerce import (
    remove_cart_item as remove_cart_item_service,
)
from app.services.commerce import (
    update_cart_item as update_cart_item_service,
)

router = APIRouter(prefix="/cart", tags=["Savat"])


@router.get("", response_model=SavatJavobi)
def read_cart(
    db: Session = Depends(get_db), user: Foydalanuvchi = Depends(get_current_user)
) -> SavatJavobi:
    """Joriy foydalanuvchining savati va umumiy summasini ko‘rsatadi."""
    return get_cart(db, user.id)


@router.post("/items", response_model=SavatJavobi, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: SavatMahsulotiYaratish,
    db: Session = Depends(get_db),
    user: Foydalanuvchi = Depends(get_current_user),
) -> SavatJavobi:
    """Mahsulotni foydalanuvchining shaxsiy savatiga qo‘shadi."""
    return add_cart_item_service(db, user.id, payload.product_id, payload.quantity)


@router.patch("/items/{product_id}", response_model=SavatJavobi)
def update_cart_item(
    product_id: int,
    payload: SavatMahsulotiYangilash,
    db: Session = Depends(get_db),
    user: Foydalanuvchi = Depends(get_current_user),
) -> SavatJavobi:
    """Savatdagi mahsulot miqdorini o‘zgartiradi."""
    return update_cart_item_service(db, user.id, product_id, payload.quantity)


@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(
    product_id: int,
    db: Session = Depends(get_db),
    user: Foydalanuvchi = Depends(get_current_user),
) -> None:
    """Mahsulotni faqat joriy foydalanuvchining savatidan olib tashlaydi."""
    remove_cart_item_service(db, user.id, product_id)
