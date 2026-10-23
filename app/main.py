from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.routers import auth, cart, categories, orders, products, users

# Tashqi API yo‘llari topshiriqdagi standart bilan mos qoladi.
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Xaridorlar uchun savat va buyurtmalarni boshqaradigan internet-do‘kon API.",
    debug=settings.DEBUG,
)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/")
def home() -> dict[str, str]:
    """API va asosiy tekshiruv manzillarini ko‘rsatadi."""
    return {
        "message": "E-commerce API ishlayapti",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Holat"])
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Xizmat va PostgreSQL ulanishi ishlayotganini tekshiradi."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
