from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Employee, User

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
    db_session.add(
        User(
            username="hr",
            hashed_password=hash_password("password123"),
            role="user",
        )
    )
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "hr",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_employee_list_includes_department_and_salary(client, db_session, auth_headers):
    db_session.add(
        Employee(
            employee_no="E2001",
            employee_name="赵六",
            gender="男",
            phone="13800002001",
            position="工艺工程师",
            department_code="DEPT-RD",
            department_name="研发部",
            hire_date=date(2020, 6, 18),
            status="在职",
            salary=12500,
        )
    )
    db_session.commit()

    resp = client.get("/api/employees?department_name=研发", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["department_code"] == "DEPT-RD"
    assert item["department_name"] == "研发部"
    assert item["employee_name"] == "赵六"
    assert item["position"] == "工艺工程师"
    assert item["phone"] == "13800002001"
    assert item["salary"] == 12500


def test_employee_list_requires_auth(client):
    resp = client.get("/api/employees")
    assert resp.status_code in (401, 403)
