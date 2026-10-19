from datetime import date, timedelta

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


@pytest.fixture()
def sample_work_hours(db_session):
    today = date.today()
    rows = [
        EmployeeWorkHour(
            employee_no="E001",
            employee_name="张三",
            department="生产一部",
            project_name="项目A",
            task_name="任务1",
            work_date=today - timedelta(days=1),
            work_hours=8,
            overtime_hours=0,
            approval_status="approved",
        ),
        EmployeeWorkHour(
            employee_no="E001",
            employee_name="张三",
            department="生产一部",
            project_name="项目A",
            task_name="任务2",
            work_date=today,
            work_hours=4,
            overtime_hours=0,
            approval_status="approved",
        ),
        EmployeeWorkHour(
            employee_no="E002",
            employee_name="李四",
            department="生产二部",
            project_name="项目B",
            task_name="任务1",
            work_date=today,
            work_hours=7.5,
            overtime_hours=0,
            approval_status="approved",
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()


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


def test_employee_work_hours_requires_auth(client):
    response = client.get("/api/reports/employee-work-hours")
    assert response.status_code == 403


def test_employee_work_hours_detail_and_employee_summary(
    client, test_user, sample_work_hours
):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    detail = client.get(
        "/api/reports/employee-work-hours?dimension=detail&page=1&page_size=10",
        headers=headers,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["total"] == 3
    assert body["dimension"] == "detail"
    assert body["items"][0]["employee_name"] == "李四"

    by_employee = client.get(
        "/api/reports/employee-work-hours?dimension=employee&page=1&page_size=10",
        headers=headers,
    )
    assert by_employee.status_code == 200
    summary = by_employee.json()
    assert summary["total"] == 2
    zhang = next(i for i in summary["items"] if i["employee_no"] == "E001")
    assert zhang["work_hours"] == 12.0
    assert zhang["record_count"] == 2


def test_employee_work_hours_department_filter(
    client, test_user, sample_work_hours
):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/reports/employee-work-hours?dimension=detail&department=生产二部",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_employee_work_hours_filters(client, test_user, sample_work_hours):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/reports/employee-work-hours/filters",
        headers=headers,
    )
    assert response.status_code == 200
    departments = response.json()["departments"]
    assert "生产一部" in departments
    assert "生产二部" in departments
