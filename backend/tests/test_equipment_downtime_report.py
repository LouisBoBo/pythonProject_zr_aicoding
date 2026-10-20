from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Equipment, EquipmentRuntimeLog, User

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
        username="downtime_tester",
        hashed_password=hash_password("password123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    response = client.post(
        "/api/auth/login",
        json={"username": "downtime_tester", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_downtime(db_session):
    today = date.today()
    eq = Equipment(
        equipment_code="EQ-DT-01",
        name="测试注塑机",
        department="注塑车间",
        status="运行",
    )
    db_session.add(eq)
    db_session.flush()
    start = datetime(today.year, today.month, today.day, 10, 0, 0)
    db_session.add(
        EquipmentRuntimeLog(
            equipment_id=eq.id,
            start_at=start,
            end_at=start + timedelta(hours=2),
            status="停机",
            runtime_hours=2.0,
            downtime_reason="故障停机",
        )
    )
    db_session.add(
        EquipmentRuntimeLog(
            equipment_id=eq.id,
            start_at=start - timedelta(days=1),
            end_at=start - timedelta(days=1) + timedelta(hours=1),
            status="运行",
            runtime_hours=1.0,
        )
    )
    db_session.commit()
    return eq


def test_equipment_downtime_filters(client, auth_headers, sample_downtime):
    response = client.get("/api/reports/equipment-downtime/filters", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "注塑车间" in data["workshops"]
    assert "故障停机" in data["downtime_reasons"]
    assert any(eq["equipment_code"] == "EQ-DT-01" for eq in data["equipment"])


def test_equipment_downtime_report_list(client, auth_headers, sample_downtime):
    response = client.get("/api/reports/equipment-downtime", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["summary"]["event_count"] == 1
    assert data["summary"]["total_duration_hours"] == 2.0
    assert data["summary"]["avg_duration_hours"] == 2.0
    assert data["summary"]["equipment_count"] == 1
    assert data["items"][0]["downtime_reason"] == "故障停机"
    assert len(data["trend"]) >= 1
    assert data["by_reason"][0]["label"] == "故障停机"
    assert data["top_equipment"][0]["equipment_code"] == "EQ-DT-01"


def test_equipment_downtime_report_reason_filter(client, auth_headers, sample_downtime):
    response = client.get(
        "/api/reports/equipment-downtime?downtime_reason=计划停机",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
