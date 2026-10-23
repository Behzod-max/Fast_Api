from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    """Ommaga qaytariladigan xavfsiz profil; parol xeshi kiritilmaydi."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
