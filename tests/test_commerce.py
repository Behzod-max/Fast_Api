import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def test_cart_ownership_and_quantity_validation(client, catalog, customer_token):
    headers, _, product = catalog
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    assert client.get("/cart", headers=customer_headers).json()["items"] == []
    assert (
        client.post(
            "/cart/items",
            json={"product_id": product["id"], "quantity": 1},
            headers=customer_headers,
        ).status_code
        == 201
    )
    assert client.get("/cart", headers=headers).json()["items"] == []
    bad_quantity = client.post(
        "/cart/items",
        json={"product_id": product["id"], "quantity": 0},
        headers=customer_headers,
    )
    assert bad_quantity.status_code == 422


def test_add_cart_item_beyond_stock_returns_conflict(client, catalog, customer_token):
    _, _, product = catalog
    response = client.post(
        "/cart/items",
        json={"product_id": product["id"], "quantity": 4},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert response.status_code == 409


def test_checkout_stock_snapshot_empty_cart_and_best_sellers(
    client, catalog, customer_token
):
    admin_headers, _, product = catalog
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    assert client.post("/orders", headers=customer_headers).status_code == 409

    assert (
        client.post(
            "/cart/items",
            json={"product_id": product["id"], "quantity": 2},
            headers=customer_headers,
        ).status_code
        == 201
    )
    order_response = client.post("/orders", headers=customer_headers)
    assert order_response.status_code == 201
    order = order_response.json()
    assert order["total_amount"] == "25.00"
    assert order["items"][0]["unit_price"] == "12.50"
    assert client.get("/cart", headers=customer_headers).json()["items"] == []

    changed = client.patch(
        f"/products/{product['id']}", json={"price": "20.00"}, headers=admin_headers
    )
    assert changed.status_code == 200
    persisted = client.get(f"/orders/{order['id']}", headers=customer_headers).json()
    assert persisted["items"][0]["unit_price"] == "12.50"
    assert persisted["total_amount"] == "25.00"
    assert client.get("/products", params={"search": "FastAPI"}).json()[0]["stock"] == 1
    best_seller = client.get("/products/best-sellers").json()
    assert best_seller[0]["sold_units"] == 2
    client.patch(f"/products/{product['id']}", json={"stock": 3}, headers=admin_headers)
    assert (
        client.post(
            "/cart/items",
            json={"product_id": product["id"], "quantity": 2},
            headers=customer_headers,
        ).status_code
        == 201
    )
    client.patch(f"/products/{product['id']}", json={"stock": 1}, headers=admin_headers)
    assert client.post("/orders", headers=customer_headers).status_code == 409
    assert client.get(f"/products/{product['id']}").json()["stock"] == 1
    assert (
        client.get("/cart", headers=customer_headers).json()["items"][0]["quantity"]
        == 2
    )
    assert (
        client.delete(f"/products/{product['id']}", headers=admin_headers).status_code
        == 409
    )


def test_cart_quantity_update_and_remove(client, catalog, customer_token):
    _, _, product = catalog
    headers = {"Authorization": f"Bearer {customer_token}"}
    assert (
        client.post(
            "/cart/items",
            json={"product_id": product["id"], "quantity": 1},
            headers=headers,
        ).status_code
        == 201
    )
    changed = client.patch(
        f"/cart/items/{product['id']}", json={"quantity": 2}, headers=headers
    )
    assert changed.status_code == 200
    assert changed.json()["items"][0]["quantity"] == 2
    assert (
        client.delete(f"/cart/items/{product['id']}", headers=headers).status_code
        == 204
    )
    assert (
        client.delete(f"/cart/items/{product['id']}", headers=headers).status_code
        == 404
    )


def test_order_history_is_private(client, catalog, customer_token):
    _, _, product = catalog
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    second = client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "strong-pass-123"},
    )
    token = client.post(
        "/auth/login",
        json={"email": "other@example.com", "password": "strong-pass-123"},
    ).json()["access_token"]
    client.post(
        "/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=customer_headers,
    )
    order_id = client.post("/orders", headers=customer_headers).json()["id"]
    assert second.status_code == 201
    assert (
        client.get(
            f"/orders/{order_id}", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 404
    )
    assert client.get("/orders", headers=customer_headers).json()[0]["id"] == order_id
    assert (
        client.get("/orders", headers={"Authorization": f"Bearer {token}"}).json() == []
    )


def test_checkout_rolls_back_all_stock_and_cart_when_one_line_is_short(
    client, catalog, customer_token
):
    headers, category, first = catalog
    second = client.post(
        "/products",
        json={
            "name": "Second",
            "price": "2.00",
            "stock": 3,
            "category_id": category["id"],
        },
        headers=headers,
    ).json()
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    for product in (first, second):
        assert (
            client.post(
                "/cart/items",
                json={"product_id": product["id"], "quantity": 2},
                headers=customer_headers,
            ).status_code
            == 201
        )
    client.patch(f"/products/{second['id']}", json={"stock": 1}, headers=headers)
    assert client.post("/orders", headers=customer_headers).status_code == 409
    products = {row["id"]: row for row in client.get("/products").json()}
    assert products[first["id"]]["stock"] == 3
    assert products[second["id"]]["stock"] == 1
    assert len(client.get("/cart", headers=customer_headers).json()["items"]) == 2


@pytest.mark.skipif(
    TEST_DATABASE_URL is None or not TEST_DATABASE_URL.startswith("postgresql"),
    reason="Concurrent checkout locking is verified against PostgreSQL in CI",
)
def test_concurrent_checkouts_do_not_oversell(client, admin_token):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    category = client.post(
        "/categories", json={"name": "Limited"}, headers=admin_headers
    ).json()
    product = client.post(
        "/products",
        json={
            "name": "Last unit",
            "price": "1.00",
            "stock": 1,
            "category_id": category["id"],
        },
        headers=admin_headers,
    ).json()

    tokens = []
    for email in ("buyer-one@example.com", "buyer-two@example.com"):
        client.post(
            "/auth/register",
            json={"email": email, "password": "strong-pass-123"},
        )
        tokens.append(
            client.post(
                "/auth/login",
                json={"email": email, "password": "strong-pass-123"},
            ).json()["access_token"]
        )
    for token in tokens:
        client.post(
            "/cart/items",
            json={"product_id": product["id"], "quantity": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

    barrier = Barrier(2)

    def purchase(token):
        with TestClient(app) as parallel_client:
            barrier.wait()
            return parallel_client.post(
                "/orders", headers={"Authorization": f"Bearer {token}"}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(purchase, tokens))

    assert sorted(statuses) == [201, 409]
    assert client.get(f"/products/{product['id']}").json()["stock"] == 0
