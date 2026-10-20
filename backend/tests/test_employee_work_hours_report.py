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
def sample_work_hours(db_session):
    today = date.today()
    yesterday = today - timedelta(days=1)
    db_session.add_all(
        [
            EmployeeWorkHour(
                employee_no="E1001",
                employee_name="张三",
                department="生产一部",
                project_name="项目A",
                task_name="任务1",
                work_date=today,
                work_hours=10.0,
                overtime_hours=1.5,
                approval_status="approved",
            ),
            EmployeeWorkHour(
                employee_no="E1002",
                employee_name="李四",
                department="生产二部",
                project_name="项目B",
                task_name="任务2",
                work_date=yesterday,
                work_hours=8.0,
                overtime_hours=0.0,
                approval_status="approved",
            ),
        ]
    )
    db_session.commit()


def test_employee_work_hours_requires_auth(client):
    response = client.get("/api/reports/employee-work-hours")
    assert response.status_code == 401


def test_employee_work_hours_filters(client, auth_headers, sample_work_hours):
    response = client.get(
        "/api/reports/employee-work-hours/filters",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "生产一部" in data["departments"]
    assert len(data["employees"]) == 2


def test_employee_work_hours_dimensions(client, auth_headers, sample_work_hours):
    by_employee = client.get(
        "/api/reports/employee-work-hours?dimension=employee",
        headers=auth_headers,
    )
    assert by_employee.status_code == 200
    assert by_employee.json()["total"] == 2
    zhang_total = next(
        i for i in by_employee.json()["items"] if i["employee_no"] == "E1001"
    )
    assert zhang_total["work_hours"] == 10.0
    assert zhang_total["work_date"] is None

    by_date = client.get(
        "/api/reports/employee-work-hours?dimension=employee_date",
        headers=auth_headers,
    )
    assert by_date.status_code == 200
    assert by_date.json()["total"] == 2
    zhang_row = next(
        i for i in by_date.json()["items"] if i["employee_no"] == "E1001"
    )
    assert zhang_row["work_hours"] == 10.0
    assert zhang_row["overtime_hours"] == 1.5

    by_project = client.get(
        "/api/reports/employee-work-hours?dimension=project",
        headers=auth_headers,
    )
    assert by_project.json()["total"] == 2

    by_dept = client.get(
        "/api/reports/employee-work-hours?dimension=department",
        headers=auth_headers,
    )
    assert by_dept.json()["total"] == 2


def test_employee_work_hours_department_filter(client, auth_headers, sample_work_hours):
    response = client.get(
        "/api/reports/employee-work-hours?dimension=detail&department=生产一部",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["employee_no"] == "E1001"


def test_employee_work_hours_invalid_dimension(client, auth_headers, sample_work_hours):
    response = client.get(
        "/api/reports/employee-work-hours?dimension=invalid",
        headers=auth_headers,
    )
    assert response.status_code == 400
