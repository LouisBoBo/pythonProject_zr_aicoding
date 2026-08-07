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


def _work_order_payload(order_no="WO20250807001", **overrides):
    payload = {
        "order_no": order_no,
        "product_name": "测试产品",
        "product_code": "P001",
        "production_line": "A线",
        "plan_quantity": 100,
        "priority": "normal",
        "assignee": "张三",
        "start_date": "2025-08-07",
        "end_date": "2025-08-10",
        "remark": "测试备注",
    }
    payload.update(overrides)
    return payload


def test_create_work_order_without_token(client):
    response = client.post(
        "/api/work-orders",
        json=_work_order_payload(),
    )
    assert response.status_code == 403


def test_create_and_list_work_orders(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(priority="high"),
        headers=headers,
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["order_no"] == "WO20250807001"
    assert data["product_name"] == "测试产品"
    assert data["priority"] == "high"
    assert data["status"] == "pending"
    assert data["actual_quantity"] == 0
    assert data["remark"] == "测试备注"

    list_response = client.get("/api/work-orders", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["order_no"] == data["order_no"]


def test_create_work_order_minimal_fields(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/work-orders",
        json={
            "order_no": "WO-MIN-001",
            "product_name": "最小字段产品",
            "plan_quantity": 10,
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["order_no"] == "WO-MIN-001"
    assert data["status"] == "pending"
    assert data["actual_quantity"] == 0


def test_duplicate_order_no_returns_409(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}
    payload = _work_order_payload(order_no="WO-DUP-001")

    first = client.post("/api/work-orders", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post("/api/work-orders", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"] == "工单号已存在"


def test_list_work_orders_filter_by_status(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-FILTER-001"),
        headers=headers,
    )

    pending_response = client.get("/api/work-orders?status=pending", headers=headers)
    assert pending_response.status_code == 200
    assert pending_response.json()["total"] == 1

    completed_response = client.get("/api/work-orders?status=completed", headers=headers)
    assert completed_response.status_code == 200
    assert completed_response.json()["total"] == 0


def test_list_work_orders_filter_by_priority(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-PRI-001", priority="high"),
        headers=headers,
    )
    client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-PRI-002", priority="low"),
        headers=headers,
    )

    high_response = client.get("/api/work-orders?priority=high", headers=headers)
    assert high_response.status_code == 200
    assert high_response.json()["total"] == 1
    assert high_response.json()["items"][0]["order_no"] == "WO-PRI-001"


def test_get_work_order_detail(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-DETAIL-001"),
        headers=headers,
    )
    work_order_id = create_response.json()["id"]

    detail_response = client.get(f"/api/work-orders/{work_order_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["order_no"] == "WO-DETAIL-001"

    not_found = client.get("/api/work-orders/9999", headers=headers)
    assert not_found.status_code == 404


def test_update_work_order(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-UPD-001"),
        headers=headers,
    )
    work_order_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/work-orders/{work_order_id}",
        json={"product_name": "更新后的产品", "actual_quantity": 50},
        headers=headers,
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["product_name"] == "更新后的产品"
    assert data["actual_quantity"] == 50


def test_work_order_status_transitions(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-STATUS-001"),
        headers=headers,
    )
    work_order_id = create_response.json()["id"]

    start_response = client.patch(
        f"/api/work-orders/{work_order_id}/status",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "in_progress"

    complete_response = client.patch(
        f"/api/work-orders/{work_order_id}/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    invalid_response = client.patch(
        f"/api/work-orders/{work_order_id}/status",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert invalid_response.status_code == 400


def test_cancel_work_order(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-CANCEL-001"),
        headers=headers,
    )
    work_order_id = create_response.json()["id"]

    cancel_response = client.patch(
        f"/api/work-orders/{work_order_id}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_delete_work_order(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-DEL-001"),
        headers=headers,
    )
    work_order_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/work-orders/{work_order_id}", headers=headers)
    assert delete_response.status_code == 204

    detail_response = client.get(f"/api/work-orders/{work_order_id}", headers=headers)
    assert detail_response.status_code == 404


def test_list_work_orders_search(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-SEARCH-001", product_name="特殊产品A"),
        headers=headers,
    )
    client.post(
        "/api/work-orders",
        json=_work_order_payload(order_no="WO-OTHER-002", product_name="普通产品B"),
        headers=headers,
    )

    search_response = client.get("/api/work-orders?product_name=特殊", headers=headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1
    assert search_response.json()["items"][0]["order_no"] == "WO-SEARCH-001"
