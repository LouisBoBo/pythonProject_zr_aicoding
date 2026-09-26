"""设备看板 /api/device/* 路由存在性（非 404）。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _token(client):
    r = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/device/oee",
        "/api/device/utilization?period=day",
        "/api/device/alarms/trend",
        "/api/device/status/summary",
        "/api/device/list",
        "/api/device/output",
    ],
)
def test_device_routes_not_404(client, test_user, path):
    token = _token(client)
    r = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_device_oee_shape(client, test_user):
    token = _token(client)
    r = client.get("/api/device/oee", headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    for key in ("availability", "performance", "quality", "oee"):
        assert key in body
