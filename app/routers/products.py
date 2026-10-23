from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.cart_item import SavatMahsuloti
from app.models.category import Kategoriya
from app.models.order import BuyurtmaMahsuloti
from app.models.product import Mahsulot
from app.models.user import Foydalanuvchi
from app.schemas.product import (
    MahsulotJavobi,
    MahsulotSavdosiJavobi,
    MahsulotYangilash,
    MahsulotYaratish,
)

router = APIRouter(prefix="/products", tags=["Mahsulotlar"])


@router.post("", response_model=MahsulotJavobi, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: MahsulotYaratish,
    db: Session = Depends(get_db),
    _admin: Foydalanuvchi = Depends(require_admin),
) -> Mahsulot:
    """Yangi mahsulot yaratadi; kategoriya mavjudligi tekshiriladi."""
    if db.get(Kategoriya, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    product = Mahsulot(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[MahsulotJavobi])
def list_products(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = Query(default=None, gt=0),
    min_price: Decimal | None = Query(default=None, gt=0),
    max_price: Decimal | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[Mahsulot]:
    """Mahsulotlarni nom, kategoriya va narx oralig‘i bo‘yicha sahifalab topadi."""
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=422,
            detail="Eng past narx eng yuqori narxdan katta bo‘lishi mumkin emas",
        )
    query = select(Mahsulot)
    if search:
        query = query.where(Mahsulot.name.ilike(f"%{search.strip()}%"))
    if category_id is not None:
        query = query.where(Mahsulot.category_id == category_id)
    if min_price is not None:
        query = query.where(Mahsulot.price >= min_price)
    if max_price is not None:
        query = query.where(Mahsulot.price <= max_price)
    return list(db.scalars(query.order_by(Mahsulot.id).offset(offset).limit(limit)))


@router.get("/best-sellers", response_model=list[MahsulotSavdosiJavobi])
def best_sellers(
    limit: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db)
) -> list[MahsulotSavdosiJavobi]:
    """Faqat muvaffaqiyatli buyurtmalardagi sotuvlar bo‘yicha reytingni qaytaradi."""
    rows = db.execute(
        select(Mahsulot, func.sum(BuyurtmaMahsuloti.quantity).label("sold_units"))
        .join(BuyurtmaMahsuloti, BuyurtmaMahsuloti.product_id == Mahsulot.id)
        .group_by(Mahsulot.id)
        .order_by(func.sum(BuyurtmaMahsuloti.quantity).desc(), Mahsulot.id)
        .limit(limit)
    )
    return [
        MahsulotSavdosiJavobi.model_validate(
            {
                **MahsulotJavobi.model_validate(product).model_dump(),
                "sold_units": sold_units,
            }
        )
        for product, sold_units in rows
    ]


@router.get("/{product_id}", response_model=MahsulotJavobi)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Mahsulot:
    """Bitta mahsulot tafsilotlarini qaytaradi."""
    product = db.get(Mahsulot, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product


@router.patch("/{product_id}", response_model=MahsulotJavobi)
def update_product(
    product_id: int,
    payload: MahsulotYangilash,
    db: Session = Depends(get_db),
    _admin: Foydalanuvchi = Depends(require_admin),
) -> Mahsulot:
    """Mahsulot maydonlarini yangilaydi; faqat administratorga ruxsat beriladi."""
    product = db.get(Mahsulot, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and db.get(Kategoriya, changes["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    for key, value in changes.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: Foydalanuvchi = Depends(require_admin),
) -> None:
    """Buyurtma tarixini saqlab, faqat tarixga kirmagan mahsulotni o‘chiradi."""
    product = db.get(Mahsulot, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    if (
        db.scalar(
            select(BuyurtmaMahsuloti.id).where(BuyurtmaMahsuloti.product_id == product_id).limit(1)
        )
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Mahsulot buyurtma tarixida bor, uni o‘chirib bo‘lmaydi",
        )
    db.query(SavatMahsuloti).filter(SavatMahsuloti.product_id == product_id).delete(
        synchronize_session=False
    )
    db.delete(product)
    db.commit()
