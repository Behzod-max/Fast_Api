from pydantic import BaseModel, EmailStr, Field


class RoyxatdanOtishSorovi(BaseModel):
    """Ro‘yxatdan o‘tish maydonlari; rol ataylab qabul qilinmaydi."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TizimgaKirishSorovi(BaseModel):
    """Kirish uchun email va parol."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenJavobi(BaseModel):
    """JWT access token javobining formati."""

    access_token: str
    token_type: str = "bearer"
