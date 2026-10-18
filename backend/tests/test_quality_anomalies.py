"""R08：品质异常列表筛选与关闭。"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import QualityAnomaly, User

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
        User(username="qa", hashed_password=hash_password("pass123"), role="admin")
    )
    db_session.commit()
    token = client.post(
        "/api/auth/login",
        json={
            "username": "qa",
            "password": "pass123",
            "enterprise_code": "前海中软",
        },
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def anomalies(db_session):
    rows = [
        QualityAnomaly(
            production_line="SMT-1",
            process="贴片",
            defect_type="虚焊",
            severity="major",
            status="open",
            discovered_at=datetime.utcnow(),
        ),
        QualityAnomaly(
            production_line="DIP",
            process="焊接",
            defect_type="短路",
            severity="minor",
            status="closed",
            handler="张三",
            resolution_note="已返修",
            discovered_at=datetime.utcnow(),
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()
    for r in rows:
        db_session.refresh(r)
    return rows


def test_list_anomalies_filter_open(client, auth_headers, anomalies):
    resp = client.get(
        "/api/quality/anomalies?status=open&page=1&page_size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "open"


def test_close_anomaly_requires_handler_and_note(client, auth_headers, anomalies):
    open_id = anomalies[0].id
    empty = client.post(
        f"/api/quality/anomalies/{open_id}/close",
        headers=auth_headers,
        json={"handler": "", "resolution_note": ""},
    )
    assert empty.status_code == 422

    no_note = client.post(
        f"/api/quality/anomalies/{open_id}/close",
        headers=auth_headers,
        json={"handler": "李四", "resolution_note": "  "},
    )
    assert no_note.status_code == 400

    ok = client.post(
        f"/api/quality/anomalies/{open_id}/close",
        headers=auth_headers,
        json={"handler": "李四", "resolution_note": "已复检合格"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["status"] == "closed"
    assert body["handler"] == "李四"
    assert body["resolution_note"] == "已复检合格"

    again = client.post(
        f"/api/quality/anomalies/{open_id}/close",
        headers=auth_headers,
        json={"handler": "李四", "resolution_note": "重复关闭"},
    )
    assert again.status_code == 400

    open_list = client.get(
        "/api/quality/anomalies?status=open",
        headers=auth_headers,
    ).json()
    assert open_list["total"] == 0
