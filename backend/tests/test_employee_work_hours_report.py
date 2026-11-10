from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User, WorkOrder, WorkOrderLaborRecord

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
def auth_headers(client, db_session):
    user = User(
        username="ewh_tester",
        hashed_password=hash_password("password123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": "ewh_tester", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_labor_records(db_session):
    today = date.today()
    yesterday = today - timedelta(days=1)
    wo_a = WorkOrder(
        order_no="WO-EWH-A",
        product_name="产品A",
        plan_quantity=100,
        actual_quantity=80,
        status="in_progress",
        current_process="贴片",
    )
    wo_b = WorkOrder(
        order_no="WO-EWH-B",
        product_name="产品B",
        plan_quantity=50,
        actual_quantity=40,
        status="in_progress",
        current_process="焊接",
    )
    db_session.add_all([wo_a, wo_b])
    db_session.flush()
    db_session.add_all(
        [
            WorkOrderLaborRecord(
                employee_no="E1001",
                employee_name="张三",
                department_name="生产一部",
                work_date=today,
                work_order_id=wo_a.id,
                process="贴片",
                work_hours=10.0,
            ),
            WorkOrderLaborRecord(
                employee_no="E1002",
                employee_name="李四",
                department_name="生产二部",
                work_date=yesterday,
                work_order_id=wo_b.id,
                process="焊接",
                work_hours=8.0,
            ),
        ]
    )
    db_session.commit()


def test_employee_work_hours_requires_auth(client):
    response = client.get("/api/reports/employee-work-hours")
    assert response.status_code in (401, 403)


def test_employee_work_hours_filters(client, auth_headers, sample_labor_records):
    response = client.get(
        "/api/reports/employee-work-hours/filters",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "生产一部" in data["departments"]
    assert len(data["employees"]) == 2


def test_employee_work_hours_list_and_sum(client, auth_headers, sample_labor_records):
    today = date.today().isoformat()
    response = client.get(
        f"/api/reports/employee-work-hours?date_from={today}&date_to={today}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["work_hours_sum"] == 10.0
    assert data["items"][0]["employee_no"] == "E1001"
    assert data["items"][0]["order_no"] == "WO-EWH-A"
    assert data["items"][0]["process"] == "贴片"


def test_employee_work_hours_department_filter(client, auth_headers, sample_labor_records):
    response = client.get(
        "/api/reports/employee-work-hours?department_name=生产一部",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["employee_no"] == "E1001"
