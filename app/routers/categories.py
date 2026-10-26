from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.category import Kategoriya
from app.models.product import Mahsulot
from app.models.user import Foydalanuvchi
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Kategoriyalar"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _admin: Foydalanuvchi = Depends(require_admin),
) -> Kategoriya:
    """Yangi kategoriya yaratadi; bu amal administrator uchun."""
    category = Kategoriya(**payload.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Bunday kategoriya nomi allaqachon mavjud"
        ) from None
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    offset: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> list[Kategoriya]:
    """Kategoriyalarni sahifalab ro‘yxatlaydi."""
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Sahifalash qiymatlari noto‘g‘ri")
    return list(
        db.scalars(select(Kategoriya).order_by(Kategoriya.id).offset(offset).limit(limit))
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _admin: Foydalanuvchi = Depends(require_admin),
) -> None:
    """Mahsuloti yo‘q kategoriyani o‘chiradi."""
    category = db.get(Kategoriya, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    if (
        db.scalar(select(Mahsulot.id).where(Mahsulot.category_id == category_id).limit(1))
        is not None
    ):
        raise HTTPException(
            status_code=409,
            detail="Kategoriyada mahsulotlar bor, uni o‘chirib bo‘lmaydi",
        )
    db.delete(category)
    db.commit()
