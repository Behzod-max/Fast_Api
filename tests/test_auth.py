from datetime import UTC


def test_register_returns_customer_without_password_hash(client):
    response = client.post(
        "/auth/register",
        json={"email": "New.User@example.com", "password": "strong-pass-123"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "customer"
    assert "password_hash" not in response.json()
    assert response.json()["email"] == "new.user@example.com"


def test_duplicate_registration_returns_conflict(client):
    payload = {"email": "same@example.com", "password": "strong-pass-123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_password_validation_returns_unprocessable_entity(client):
    response = client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "tiny"},
    )
    assert response.status_code == 422


def test_login_and_profile(client, customer_token):
    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "customer"
    assert "password_hash" not in response.json()


def test_wrong_password_returns_unauthorized(client):
    client.post(
        "/auth/register", json={"email": "a@example.com", "password": "strong-pass-123"}
    )
    response = client.post(
        "/auth/login", json={"email": "a@example.com", "password": "wrong-pass"}
    )
    assert response.status_code == 401


def test_invalid_and_expired_tokens_are_rejected(client):
    from datetime import datetime, timedelta

    import jwt

    from app.core.config import settings

    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    for token in ("not-a-token", expired):
        response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_profile_requires_authentication(client):
    assert client.get("/users/me").status_code == 401


def test_health_endpoint_checks_database(client):
    assert client.get("/health").json() == {"status": "ok"}
