import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./pytest.db")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-change-me-32-bytes-minimum")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import ModelAsosi
from app.db.session import get_db
from app.main import app
from app.models import *


@pytest.fixture
def test_engine():
    if TEST_DATABASE_URL is None or TEST_DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    ModelAsosi.metadata.create_all(bind=engine)
    yield engine
    ModelAsosi.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def customer_token(client):
    client.post(
        "/auth/register",
        json={"email": "customer@example.com", "password": "strong-pass-123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "strong-pass-123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client):
    from app.core.security import hash_password
    from app.db.session import get_db
    from app.models.user import Foydalanuvchi

    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    db.add(
        Foydalanuvchi(
            email="admin@example.com",
            password_hash=hash_password("admin-pass-123"),
            role="admin",
        )
    )
    db.commit()
    generator.close()
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "admin-pass-123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def catalog(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    category = client.post("/categories", json={"name": "Books"}, headers=headers)
    assert category.status_code == 201
    product = client.post(
        "/products",
        json={
            "name": "FastAPI Guide",
            "description": "Backend engineering",
            "price": "12.50",
            "stock": 3,
            "category_id": category.json()["id"],
        },
        headers=headers,
    )
    assert product.status_code == 201
    return headers, category.json(), product.json()
