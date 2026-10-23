from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BuyurtmaMahsulotiJavobi(BaseModel):
    """Buyurtmadagi mahsulotning xarid paytida saqlangan narxi."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal


class BuyurtmaJavobi(BaseModel):
    """Buyurtma sarlavhasi va uning tarixiy qatorlari."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    total_amount: Decimal
    created_at: datetime
    items: list[BuyurtmaMahsulotiJavobi]
