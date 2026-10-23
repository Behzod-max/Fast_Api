from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.product import ProductRead


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=2_147_483_647)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=2_147_483_647)


class CartLine(BaseModel):
    product: ProductRead
    quantity: int
    line_total: Decimal


class CartRead(BaseModel):
    items: list[CartLine]
    total_amount: Decimal
