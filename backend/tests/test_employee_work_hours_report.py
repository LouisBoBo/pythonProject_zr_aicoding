from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import EmployeeWorkHour, User

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
        username="report_wh",
        hashed_password=hash_password("test123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    resp = client.post("/api/auth/login", json={"username": "report_wh", "password": "test123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_work_hours(db_session):
    db_session.add_all(
        [
            EmployeeWorkHour(
                employee_no="E1001",
                employee_name="张三",
                department="生产部",
                project_name="项目A",
                task_name="任务1",
                work_date=date(2026, 11, 10),
                shift_type="day",
                work_hours=8.0,
                overtime_hours=1.5,
                approval_status="approved",
                created_at=datetime.utcnow(),
            ),
            EmployeeWorkHour(
                employee_no="E1001",
                employee_name="张三",
                department="生产部",
                project_name="项目B",
                task_name="任务2",
                work_date=date(2026, 11, 10),
                shift_type="day",
                work_hours=2.0,
                overtime_hours=0.0,
                approval_status="approved",
                created_at=datetime.utcnow(),
            ),
            EmployeeWorkHour(
                employee_no="E2002",
                employee_name="李四",
                department="质检部",
                project_name="项目A",
                task_name="任务1",
                work_date=date(2026, 11, 11),
                shift_type="night",
                work_hours=7.5,
                overtime_hours=0.5,
                approval_status="approved",
                created_at=datetime.utcnow(),
            ),
        ]
    )
    db_session.commit()


def test_employee_work_hours_report_filters(client, auth_headers, sample_work_hours):
    resp = client.get("/api/reports/employee-work-hours/filters", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "生产部" in data["departments"]
    assert any(e["employee_no"] == "E1001" for e in data["employees"])


def test_employee_work_hours_report_employee_date(client, auth_headers, sample_work_hours):
    resp = client.get(
        "/api/reports/employee-work-hours?dimension=employee_date&page=1&page_size=20",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["work_hours_sum"] == 18.0
    assert data["total_work_hours_sum"] == 20.0
    zhang = next(i for i in data["items"] if i["employee_no"] == "E1001")
    assert zhang["work_hours"] == 10.0
    assert zhang["work_order_count"] == 2
    assert zhang["total_work_hours"] == 11.5
    assert zhang["shift_type"] == "day"
    assert zhang["shift_type_label"] == "白班"
    li = next(i for i in data["items"] if i["employee_no"] == "E2002")
    assert li["shift_type_label"] == "晚班"


def test_employee_work_hours_report_department_filter(client, auth_headers, sample_work_hours):
    resp = client.get(
        "/api/reports/employee-work-hours?department=质检部&dimension=employee_date",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["employee_no"] == "E2002"


def test_employee_work_hours_report_export(client, auth_headers, sample_work_hours):
    resp = client.get("/api/reports/employee-work-hours/export", headers=auth_headers)
    assert resp.status_code == 200
    assert (
        resp.headers.get("content-type", "")
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 100


def test_employee_work_hours_report_requires_auth(client):
    resp = client.get("/api/reports/employee-work-hours")
    assert resp.status_code == 401
