def test_customer_cannot_manage_catalog(client, customer_token):
    headers = {"Authorization": f"Bearer {customer_token}"}
    assert (
        client.post("/categories", json={"name": "Nope"}, headers=headers).status_code
        == 403
    )
    assert (
        client.post(
            "/products",
            json={"name": "Nope", "price": "1.00", "stock": 1, "category_id": 1},
            headers=headers,
        ).status_code
        == 403
    )


def test_category_and_product_create_list_filter_and_detail(client, catalog):
    _, category, product = catalog
    response = client.get(
        "/products",
        params={
            "search": "fastapi",
            "category_id": category["id"],
            "min_price": "10",
            "max_price": "15",
        },
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [product["id"]]
    assert client.get(f"/products/{product['id']}").json()["name"] == "FastAPI Guide"
    assert client.get("/categories").json()[0]["name"] == "Books"


def test_duplicate_category_returns_conflict(client, catalog):
    headers, _, _ = catalog
    assert (
        client.post("/categories", json={"name": "Books"}, headers=headers).status_code
        == 409
    )


def test_invalid_product_price_and_filter_are_rejected(client, catalog):
    headers, category, _ = catalog
    invalid = client.post(
        "/products",
        json={"name": "Bad", "price": "0", "stock": 1, "category_id": category["id"]},
        headers=headers,
    )
    assert invalid.status_code == 422
    assert (
        client.get("/products", params={"min_price": 20, "max_price": 10}).status_code
        == 422
    )


def test_product_update_delete_and_missing_product(client, catalog):
    headers, _, product = catalog
    updated = client.patch(
        f"/products/{product['id']}", json={"price": "15.00"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == "15.00"
    assert client.get("/products/999").status_code == 404
    assert (
        client.delete(f"/products/{product['id']}", headers=headers).status_code == 204
    )


def test_non_nullable_product_fields_reject_null_updates(client, catalog):
    headers, _, product = catalog
    response = client.patch(
        f"/products/{product['id']}", json={"price": None}, headers=headers
    )
    assert response.status_code == 422


def test_category_cannot_be_deleted_while_products_exist(client, catalog):
    headers, category, _ = catalog
    assert (
        client.delete(f"/categories/{category['id']}", headers=headers).status_code
        == 409
    )
    assert client.get("/categories").json()[0]["id"] == category["id"]
