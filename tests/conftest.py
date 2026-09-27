import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.models.user import User
from app.core.security import hash_password

# A fresh in-memory SQLite DB per test-session; each test function gets a
# clean set of tables (see `db` fixture below) so tests don't leak state
# into each other.
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    def _make_user(email="user@example.com", password="password123", is_admin=False):
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test User",
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user


@pytest.fixture()
def auth_headers(client, make_user):
    def _auth_headers(email="user@example.com", password="password123", is_admin=False):
        make_user(email=email, password=password, is_admin=is_admin)
        resp = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture()
def centre_with_test(db):
    centre = DiagnosticCentre(name="City Diagnostics", location="Indore")
    db.add(centre)
    db.commit()
    db.refresh(centre)

    test = DiagnosticTest(centre_id=centre.id, name="Complete Blood Count", price=499.00)
    db.add(test)
    db.commit()
    db.refresh(test)

    return centre, test


@pytest.fixture()
def future_time():
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
