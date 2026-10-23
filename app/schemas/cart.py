from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.product import MahsulotJavobi


class SavatMahsulotiYaratish(BaseModel):
    """Savatga qo‘shiladigan mahsulot identifikatori va miqdori."""

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=2_147_483_647)


class SavatMahsulotiYangilash(BaseModel):
    """Savatdagi mahsulot miqdorini yangilash ma’lumoti."""

    quantity: int = Field(gt=0, le=2_147_483_647)


class SavatQatori(BaseModel):
    """Savatdagi bitta mahsulot va hisoblangan qator summasi."""

    product: MahsulotJavobi
    quantity: int
    line_total: Decimal


class SavatJavobi(BaseModel):
    """Savat tarkibi va umumiy summa."""

    items: list[SavatQatori]
    total_amount: Decimal
