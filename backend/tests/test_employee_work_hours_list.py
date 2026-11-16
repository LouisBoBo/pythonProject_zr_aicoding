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
        username="admin_wh",
        hashed_password=hash_password("test123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    resp = client.post("/api/auth/login", json={"username": "admin_wh", "password": "test123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_hours(db_session):
    row = EmployeeWorkHour(
        employee_no="E001",
        employee_name="张三",
        department="生产部",
        project_name="项目A",
        task_name="任务1",
        work_date=date(2026, 11, 10),
        work_hours=8.0,
        overtime_hours=1.0,
        approval_status="approved",
        created_at=datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()


def test_employee_work_hours_list_ok(client, auth_headers, sample_hours):
    resp = client.get("/api/employee-work-hours?page=1&page_size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["employee_name"] == "张三"
    assert data["items"][0]["approval_status"] == "已通过"


def test_employee_work_hours_list_requires_auth(client):
    resp = client.get("/api/employee-work-hours")
    assert resp.status_code == 401
