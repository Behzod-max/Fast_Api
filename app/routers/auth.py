from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import Foydalanuvchi
from app.schemas.auth import RoyxatdanOtishSorovi, TizimgaKirishSorovi, TokenJavobi
from app.schemas.user import FoydalanuvchiJavobi

router = APIRouter(prefix="/auth", tags=["Autentifikatsiya"])


@router.post("/register", response_model=FoydalanuvchiJavobi, status_code=status.HTTP_201_CREATED)
def register(payload: RoyxatdanOtishSorovi, db: Session = Depends(get_db)) -> Foydalanuvchi:
    """Xaridor hisobini yaratadi; ro‘yxatdan o‘tgan foydalanuvchi admin bo‘la olmaydi."""
    email = str(payload.email).lower()
    if db.scalar(select(Foydalanuvchi).where(Foydalanuvchi.email == email)) is not None:
        raise HTTPException(
            status_code=409, detail="Bu elektron pochta allaqachon ro‘yxatdan o‘tgan"
        )
    user = Foydalanuvchi(
        email=email, password_hash=hash_password(payload.password), role="customer"
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Bu elektron pochta allaqachon ro‘yxatdan o‘tgan"
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenJavobi)
def login(payload: TizimgaKirishSorovi, db: Session = Depends(get_db)) -> TokenJavobi:
    """Hisob ma’lumotlarini tekshiradi va amal qilish muddati bor JWT beradi."""
    email = str(payload.email).lower()
    user = db.scalar(select(Foydalanuvchi).where(Foydalanuvchi.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Elektron pochta yoki parol noto‘g‘ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenJavobi(access_token=create_access_token(str(user.id)))
