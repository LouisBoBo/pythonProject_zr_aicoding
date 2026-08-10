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
    db_session.refresh(user)
    return user


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_with_test_enterprise(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "测试企业",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_success_with_full_enterprise_name(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软电子有限公司",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "wrong",
            "enterprise_code": "前海中软",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "账号或密码错误"


def test_login_unknown_user(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "nobody",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    assert response.status_code == 401


def test_login_missing_enterprise_code(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 422


def test_login_invalid_enterprise_code(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "无效企业",
        },
    )
    assert response.status_code == 422


def test_me_with_valid_token(client, test_user):
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "前海中软",
        },
    )
    token = login_response.json()["access_token"]
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "user"


def test_me_without_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 403
