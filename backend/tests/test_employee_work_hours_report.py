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
def auth_headers(client, test_user):
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_work_hours(db_session):
    from datetime import date, timedelta

    today = date.today()
    rows = [
        EmployeeWorkHour(
            employee_no="E1001",
            employee_name="张三",
            department="生产一部",
            project_name="项目A",
            task_name="任务1",
            work_date=today - timedelta(days=1),
            work_hours=8.0,
            overtime_hours=1.0,
            approval_status="approved",
        ),
        EmployeeWorkHour(
            employee_no="E1001",
            employee_name="张三",
            department="生产一部",
            project_name="项目A",
            task_name="任务2",
            work_date=today - timedelta(days=1),
            work_hours=2.0,
            overtime_hours=0.5,
            approval_status="pending",
        ),
        EmployeeWorkHour(
            employee_no="E1002",
            employee_name="李四",
            department="研发部",
            project_name="项目B",
            task_name="任务3",
            work_date=today - timedelta(days=2),
            work_hours=7.0,
            overtime_hours=0.0,
            approval_status="approved",
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def test_employee_work_hours_requires_auth(client):
    response = client.get("/api/reports/employee-work-hours")
    assert response.status_code == 403


def test_employee_work_hours_detail_and_filters(client, auth_headers, sample_work_hours):
    resp = client.get("/api/reports/employee-work-hours", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # 明细默认展示全部（含 pending），合计仅已通过：8+7=15
    assert data["total"] == 3
    assert data["dimension"] == "detail"
    assert data["items"][0]["employee_name"] == "张三"
    assert data["work_hours_sum"] == 15.0

    filtered = client.get(
        "/api/reports/employee-work-hours?department=研发部",
        headers=auth_headers,
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["employee_name"] == "李四"


def test_employee_work_hours_approval_status_filter(client, auth_headers, sample_work_hours):
    pending = client.get(
        "/api/reports/employee-work-hours?approval_status=pending",
        headers=auth_headers,
    )
    assert pending.status_code == 200
    assert pending.json()["total"] == 1
    assert pending.json()["items"][0]["approval_status"] == "待审批"

    bad = client.get(
        "/api/reports/employee-work-hours?approval_status=xxx",
        headers=auth_headers,
    )
    assert bad.status_code == 400


def test_employee_work_hours_batch_approval(client, auth_headers, sample_work_hours):
    pending_id = next(r.id for r in sample_work_hours if r.approval_status == "pending")
    resp = client.post(
        "/api/reports/employee-work-hours/batch-approval",
        headers=auth_headers,
        json={"ids": [pending_id], "approval_status": "approved"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
    # 再次审批同一条：已非 pending，updated=0
    again = client.post(
        "/api/reports/employee-work-hours/batch-approval",
        headers=auth_headers,
        json={"ids": [pending_id], "approval_status": "rejected"},
    )
    assert again.json()["updated"] == 0


def test_employee_work_hours_dimensions(client, auth_headers, sample_work_hours):
    by_employee = client.get(
        "/api/reports/employee-work-hours?dimension=employee",
        headers=auth_headers,
    )
    assert by_employee.status_code == 200
    # 非明细默认已通过：张三仅 8h（不含 pending 2h）
    assert by_employee.json()["total"] == 2
    zhang_total = next(
        i for i in by_employee.json()["items"] if i["employee_no"] == "E1001"
    )
    assert zhang_total["work_hours"] == 8.0
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
    assert zhang_row["work_hours"] == 8.0
    assert zhang_row["overtime_hours"] == 1.0

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


def test_employee_work_hours_filters_endpoint(client, auth_headers, sample_work_hours):
    resp = client.get("/api/reports/employee-work-hours/filters", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "生产一部" in data["departments"]
    assert len(data["employees"]) == 2
    assert "项目A" in data["projects"]


def test_employee_work_hours_export(client, auth_headers, sample_work_hours):
    resp = client.get(
        "/api/reports/employee-work-hours/export?dimension=detail",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 100
    # 默认仅已通过：用 all 应更大（含 pending）
    all_resp = client.get(
        "/api/reports/employee-work-hours/export?dimension=detail&approval_status=all",
        headers=auth_headers,
    )
    assert all_resp.status_code == 200
    assert len(all_resp.content) >= len(resp.content)
