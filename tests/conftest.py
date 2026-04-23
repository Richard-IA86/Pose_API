"""Shared test fixtures for the POSE API test suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use an in-memory SQLite database shared across all connections in tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Create all tables once for the entire test session
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def registered_user(client: TestClient):
    """Register a test user once per session and return credentials."""
    payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Test1234",
        "full_name": "Test User",
    }
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return payload


@pytest.fixture(scope="session")
def auth_headers(client: TestClient, registered_user):
    """Return Authorization headers for the test user."""
    resp = client.post(
        "/auth/login",
        json={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def superuser_headers(client: TestClient):
    """Create a superuser and return its auth headers."""
    from app.auth.utils import create_user
    from app.database import SessionLocal

    # Create superuser directly in DB
    db = TestSessionLocal()
    try:
        from app.auth import models
        existing = db.query(models.User).filter(models.User.username == "admin").first()
        if not existing:
            user = create_user(db, "admin", "admin@example.com", "Admin1234", "Admin User")
            user.is_superuser = True
            db.commit()
    finally:
        db.close()

    resp = client.post("/auth/login", json={"username": "admin", "password": "Admin1234"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
