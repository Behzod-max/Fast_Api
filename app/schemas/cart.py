from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.product import ProductRead


class CartItemCreate(BaseModel):
    """Savatga qo‘shiladigan mahsulot identifikatori va miqdori."""

    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=2_147_483_647)


class CartItemUpdate(BaseModel):
    """Savatdagi mahsulot miqdorini yangilash ma’lumoti."""

    quantity: int = Field(gt=0, le=2_147_483_647)


class CartLine(BaseModel):
    """Savatdagi bitta mahsulot va hisoblangan qator summasi."""

    product: ProductRead
    quantity: int
    line_total: Decimal


class CartRead(BaseModel):
    """Savat tarkibi va umumiy summa."""

    items: list[CartLine]
    total_amount: Decimal
