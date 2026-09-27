def test_signup_success(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": "password123", "full_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "hashed_password" not in body  # never leak the hash


def test_signup_duplicate_email_rejected(client, make_user):
    make_user(email="dup@example.com")
    resp = client.post(
        "/auth/signup", json={"email": "dup@example.com", "password": "password123"}
    )
    assert resp.status_code == 400


def test_login_success(client, make_user):
    make_user(email="login@example.com", password="secret123")
    resp = client.post(
        "/auth/login", data={"username": "login@example.com", "password": "secret123"}
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password_rejected(client, make_user):
    make_user(email="login2@example.com", password="secret123")
    resp = client.post(
        "/auth/login", data={"username": "login2@example.com", "password": "WRONG"}
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/bookings/")
    assert resp.status_code == 401
