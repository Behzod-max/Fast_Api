import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import Foydalanuvchi

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Foydalanuvchi:
    """JWT tokenni tekshirib, unga tegishli foydalanuvchini qaytaradi."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kirish tokeni noto‘g‘ri yoki muddati tugagan",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        subject = payload.get("sub")
        user_id = int(subject)
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise unauthorized from None

    user = db.get(Foydalanuvchi, user_id)
    if user is None:
        raise unauthorized
    return user


def require_admin(user: Foydalanuvchi = Depends(get_current_user)) -> Foydalanuvchi:
    """Faqat administratorlarga ruxsat beradi."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal uchun administrator huquqi kerak",
        )
    return user
