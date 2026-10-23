from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import Foydalanuvchi
from app.schemas.user import FoydalanuvchiJavobi

router = APIRouter(prefix="/users", tags=["Foydalanuvchilar"])


@router.get("/me", response_model=FoydalanuvchiJavobi)
def read_profile(user: Foydalanuvchi = Depends(get_current_user)) -> Foydalanuvchi:
    """Token egasining maxfiy parol xeshisiz profilini qaytaradi."""
    return user
