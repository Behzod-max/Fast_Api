from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Parolni Argon2 algoritmi bilan qaytarib bo‘lmaydigan shaklda xeshlaydi."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Kiritilgan parol xeshga mosligini tekshiradi."""
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    """Foydalanuvchi identifikatori va amal qilish vaqtiga ega JWT yaratadi."""
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": subject, "exp": expires_at},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
