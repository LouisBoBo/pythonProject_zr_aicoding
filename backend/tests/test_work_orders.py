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


def _get_token(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    return response.json()["access_token"]


def test_create_work_order_without_token(client):
    response = client.post(
        "/api/work-orders",
        json={
            "product_name": "测试产品",
            "product_code": "P001",
            "production_line": "A线",
            "plan_quantity": 100,
            "priority": "normal",
            "assignee": "张三",
            "start_date": "2025-08-07",
            "end_date": "2025-08-10",
        },
    )
    assert response.status_code == 403


def test_create_and_list_work_orders(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json={
            "product_name": "测试产品",
            "product_code": "P001",
            "production_line": "A线",
            "plan_quantity": 100,
            "priority": "high",
            "assignee": "张三",
            "start_date": "2025-08-07",
            "end_date": "2025-08-10",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["order_no"].startswith("WO")
    assert data["product_name"] == "测试产品"
    assert data["priority"] == "high"

    list_response = client.get("/api/work-orders", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["order_no"] == data["order_no"]


def test_order_no_increments(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "product_name": "产品",
        "product_code": "P002",
        "production_line": "B线",
        "plan_quantity": 50,
        "priority": "low",
        "assignee": "李四",
        "start_date": "2025-08-07",
        "end_date": "2025-08-08",
    }

    first = client.post("/api/work-orders", json=payload, headers=headers).json()
    second = client.post("/api/work-orders", json=payload, headers=headers).json()

    assert first["order_no"] != second["order_no"]
    assert int(second["order_no"][-3:]) == int(first["order_no"][-3:]) + 1
