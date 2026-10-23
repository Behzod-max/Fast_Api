from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["Foydalanuvchilar"])


@router.get("/me", response_model=UserRead)
def read_profile(user: User = Depends(get_current_user)) -> User:
    """Token egasining maxfiy parol xeshisiz profilini qaytaradi."""
    return user
