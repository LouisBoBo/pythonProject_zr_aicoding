import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User, WorkOrder

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


def _get_token(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    return response.json()["access_token"]


def _add_order(db, order_no, status="pending", plan=100, actual=0, process=None, **dates):
    wo = WorkOrder(
        order_no=order_no,
        product_name=f"产品-{order_no}",
        plan_quantity=plan,
        actual_quantity=actual,
        status=status,
        current_process=process,
        start_date=dates.get("start_date"),
        end_date=dates.get("end_date"),
    )
    db.add(wo)
    db.commit()
    return wo


def test_wip_report_requires_auth(client):
    response = client.get("/api/reports/wip")
    assert response.status_code == 403


def test_wip_report_wip_metric_and_filters(client, test_user, db_session):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    _add_order(db_session, "WO-WIP-001", status="pending", plan=200, actual=0)
    _add_order(
        db_session,
        "WO-WIP-002",
        status="in_progress",
        plan=100,
        actual=30,
        process="焊接",
        start_date=__import__("datetime").date(2025, 8, 1),
        end_date=__import__("datetime").date(2025, 8, 10),
    )
    _add_order(db_session, "WO-WIP-003", status="completed", plan=100, actual=100, process="包装")
    _add_order(db_session, "WO-WIP-004", status="cancelled", plan=50, actual=0)

    resp = client.get("/api/reports/wip", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "wip"
    assert data["total"] == 2
    order_nos = {item["order_no"] for item in data["items"]}
    assert order_nos == {"WO-WIP-001", "WO-WIP-002"}

    in_progress = next(i for i in data["items"] if i["order_no"] == "WO-WIP-002")
    assert in_progress["current_process"] == "焊接"
    assert in_progress["wip_quantity"] == 70

    filtered = client.get("/api/reports/wip?process=焊接", headers=headers)
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["order_no"] == "WO-WIP-002"

    status_filtered = client.get("/api/reports/wip?status=pending", headers=headers)
    assert status_filtered.status_code == 200
    assert status_filtered.json()["total"] == 1


def test_wip_processes_list(client, test_user):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/reports/wip/processes", headers=headers)
    assert resp.status_code == 200
    processes = resp.json()["processes"]
    assert "贴片" in processes
    assert "包装" in processes


def test_work_orders_still_accessible(client, test_user, db_session):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    _add_order(db_session, "WO-KEEP-001")
    resp = client.get("/api/work-orders", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
