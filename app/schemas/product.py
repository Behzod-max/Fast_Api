from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MahsulotYaratish(BaseModel):
    """Mahsulot yaratish maydonlari va narx/qoldiq cheklovlari."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0, le=2_147_483_647)
    category_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Mahsulot nomi bo‘sh bo‘lishi mumkin emas")
        return value


class MahsulotYangilash(BaseModel):
    """Mahsulotni qisman yangilash; majburiy ustunlarni null qilish taqiqlanadi."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0, le=2_147_483_647)
    category_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_non_nullable_fields(self):
        for field in ("name", "price", "stock", "category_id"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} maydoni null bo‘lishi mumkin emas")
        if self.name is not None:
            self.name = self.name.strip()
            if not self.name:
                raise ValueError("Mahsulot nomi bo‘sh bo‘lishi mumkin emas")
        return self


class MahsulotJavobi(BaseModel):
    """Mahsulot uchun ommaviy javob sxemasi."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    stock: int
    category_id: int


class MahsulotSavdosiJavobi(MahsulotJavobi):
    """Mahsulot va muvaffaqiyatli buyurtmalardagi sotuv miqdori."""

    sold_units: int
