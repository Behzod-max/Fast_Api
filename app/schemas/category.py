from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    """Yangi kategoriya uchun tekshiriladigan ma’lumotlar."""

    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Kategoriya nomi kamida 2 ta belgidan iborat bo‘lsin")

        return value


class CategoryUpdate(BaseModel):
    """Kategoriya nomi yoki tavsifini qisman yangilash maydonlari."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()

            if len(value) < 2:
                raise ValueError("Kategoriya nomi kamida 2 ta belgidan iborat bo‘lsin")

        return value


class CategoryResponse(BaseModel):
    """API javobiga chiqariladigan kategoriya ma’lumotlari."""

    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
