from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models.cart_item import SavatMahsuloti
from app.models.order import Buyurtma, BuyurtmaMahsuloti
from app.models.product import Mahsulot
from app.models.user import Foydalanuvchi
from app.schemas.cart import SavatJavobi, SavatQatori
from app.schemas.product import MahsulotJavobi


def get_cart(db: Session, user_id: int) -> SavatJavobi:
    """Savat qatorlari va summasini serverda hisoblaydi."""
    rows = db.execute(
        select(SavatMahsuloti, Mahsulot)
        .join(Mahsulot, Mahsulot.id == SavatMahsuloti.product_id)
        .where(SavatMahsuloti.user_id == user_id)
        .order_by(SavatMahsuloti.id)
    )
    lines: list[SavatQatori] = []
    total = Decimal("0.00")
    for item, product in rows:
        line_total = product.price * item.quantity
        total += line_total
        lines.append(
            SavatQatori(
                product=MahsulotJavobi.model_validate(product),
                quantity=item.quantity,
                line_total=line_total,
            )
        )
    return SavatJavobi(items=lines, total_amount=total)


def add_cart_item(
    db: Session, user_id: int, product_id: int, quantity: int
) -> SavatJavobi:
    """Foydalanuvchi savatini qulflab, miqdorni ombordagi qoldiq bilan solishtiradi."""
    db.scalar(select(Foydalanuvchi).where(Foydalanuvchi.id == user_id).with_for_update())
    product = db.get(Mahsulot, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    item = db.scalar(
        select(SavatMahsuloti).where(
            SavatMahsuloti.user_id == user_id, SavatMahsuloti.product_id == product_id
        )
    )
    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > product.stock:
        raise HTTPException(
            status_code=409,
            detail="So‘ralgan miqdor ombordagi qoldiqdan oshib ketdi",
        )
    if item is None:
        db.add(SavatMahsuloti(user_id=user_id, product_id=product_id, quantity=quantity))
    else:
        item.quantity = new_quantity
    db.commit()
    return get_cart(db, user_id)


def update_cart_item(
    db: Session, user_id: int, product_id: int, quantity: int
) -> SavatJavobi:
    """Savat qatorini qulflab, miqdorni zaxiradan oshirmasdan yangilaydi."""
    item = db.scalar(
        select(SavatMahsuloti)
        .where(SavatMahsuloti.user_id == user_id, SavatMahsuloti.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Savatda bunday mahsulot yo‘q")
    product = db.get(Mahsulot, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    if quantity > product.stock:
        raise HTTPException(
            status_code=409,
            detail="So‘ralgan miqdor ombordagi qoldiqdan oshib ketdi",
        )
    item.quantity = quantity
    db.commit()
    return get_cart(db, user_id)


def remove_cart_item(db: Session, user_id: int, product_id: int) -> None:
    """Savat qatorini egasini tekshirib o‘chiradi."""
    item = db.scalar(
        select(SavatMahsuloti)
        .where(SavatMahsuloti.user_id == user_id, SavatMahsuloti.product_id == product_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Savatda bunday mahsulot yo‘q")
    db.delete(item)
    db.commit()


def checkout(db: Session, user_id: int) -> Buyurtma:
    """Buyurtma, narx nusxasi, zaxira va savatni bitta tranzaksiyada boshqaradi."""
    cart_rows = list(
        db.execute(
            select(SavatMahsuloti, Mahsulot)
            .join(Mahsulot, Mahsulot.id == SavatMahsuloti.product_id)
            .where(SavatMahsuloti.user_id == user_id)
            .order_by(Mahsulot.id)
            .with_for_update()
        )
    )
    if not cart_rows:
        raise HTTPException(
            status_code=409, detail="Bo‘sh savatdan buyurtma yaratib bo‘lmaydi"
        )

    total = sum(
        (product.price * cart_item.quantity for cart_item, product in cart_rows),
        start=Decimal("0.00"),
    )
    order = Buyurtma(user_id=user_id, total_amount=total)
    db.add(order)
    db.flush()

    for cart_item, product in cart_rows:
        result = db.execute(
            update(Mahsulot)
            .where(Mahsulot.id == product.id, Mahsulot.stock >= cart_item.quantity)
            .values(stock=Mahsulot.stock - cart_item.quantity)
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"{product.id}-mahsulot uchun omborda yetarli qoldiq yo‘q",
            )
        db.add(
            BuyurtmaMahsuloti(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                quantity=cart_item.quantity,
                unit_price=product.price,
            )
        )
        db.delete(cart_item)

    order_id = order.id
    db.commit()
    completed_order = db.scalar(
        select(Buyurtma).options(selectinload(Buyurtma.items)).where(Buyurtma.id == order_id)
    )
    if completed_order is None:
        raise RuntimeError("Saqlangan buyurtmani qayta o‘qib bo‘lmadi")
    return completed_order
