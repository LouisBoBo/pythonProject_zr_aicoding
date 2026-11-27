"""客诉/COPQ 与 SPC 控制图接口测试。"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.copq_store import ensure_copq_schema, seed_copq_data
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.spc_store import compute_chart, ensure_spc_schema, seed_spc_data

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


import pytest


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    ensure_copq_schema(engine)
    ensure_spc_schema(engine)
    db = TestingSessionLocal()
    try:
        seed_copq_data(db)
        seed_spc_data(db)
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
        User(username="qa_copq", hashed_password=hash_password("pass123"), role="admin")
    )
    db_session.commit()
    token = client.post(
        "/api/auth/login",
        json={
            "username": "qa_copq",
            "password": "pass123",
            "enterprise_code": "前海中软",
        },
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_customers_and_copq_summary(client, auth_headers):
    customers = client.get("/api/quality/customers", headers=auth_headers)
    assert customers.status_code == 200
    body = customers.json()
    assert body["total"] >= 1
    assert body["items"][0]["customer_code"]

    summary = client.get("/api/quality/copq-summary", headers=auth_headers)
    assert summary.status_code == 200
    data = summary.json()
    assert data["total_complaints"] >= 1
    assert data["total_copq_amount"] > 0
    assert len(data["by_customer"]) >= 1
    assert len(data["by_category"]) >= 1


def test_create_complaint(client, auth_headers):
    resp = client.post(
        "/api/quality/complaints",
        headers=auth_headers,
        json={
            "customer_code": "6901",
            "complaint_type": "质量",
            "cost_category": "claim",
            "affected_qty": 10,
            "unit_cost": 18.6,
            "product_code": "PCB-2024-A",
            "product_name": "铝基板 PCB",
            "severity": 3,
            # 客户端即使传金额也必须被忽略，服务端按 qty×unit_cost 计算
            "copq_amount": 999999,
        },
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["customer_name"] == "华东电子有限公司"
    assert abs(item["copq_amount"] - 186.0) < 0.01


def test_create_complaint_forbidden_for_viewer(client, db_session):
    db_session.add(
        User(username="viewer_copq", hashed_password=hash_password("pass123"), role="user")
    )
    db_session.commit()
    token = client.post(
        "/api/auth/login",
        json={
            "username": "viewer_copq",
            "password": "pass123",
            "enterprise_code": "前海中软",
        },
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post(
        "/api/quality/complaints",
        headers=headers,
        json={
            "customer_code": "6901",
            "complaint_type": "质量",
            "cost_category": "claim",
            "affected_qty": 1,
            "unit_cost": 1.0,
        },
    )
    assert resp.status_code == 403


def test_spc_charts_and_detail(client, auth_headers):
    listing = client.get("/api/quality/spc/charts", headers=auth_headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) >= 1
    chart_id = items[0]["id"]

    detail = client.get(f"/api/quality/spc/charts/{chart_id}", headers=auth_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["ucl"] is not None
    assert body["cl"] is not None
    assert body["lcl"] is not None
    assert len(body["points"]) >= 1

    recomputed = client.post(
        f"/api/quality/spc/charts/{chart_id}/recompute",
        headers=auth_headers,
    )
    assert recomputed.status_code == 200
    assert recomputed.json()["cl"] is not None


def test_spc_compute_i_mr():
    # 稳定序列：控制限应包围数据
    values = [10.0, 10.1, 9.9, 10.05, 9.95, 10.02, 9.98, 10.0]
    result = compute_chart(values, chart_type="I-MR", usl=10.5, lsl=9.5)
    assert result["ucl"] > result["cl"] > result["lcl"]
    assert result["cp"] is not None
    assert result["cpk"] is not None
    assert result["status"] == "normal"

    # 末尾失控点
    bad = values + [12.0]
    alert = compute_chart(bad, chart_type="I-MR")
    assert alert["status"] == "alert"
    assert 9 in alert["out_of_control_indexes"]


def test_spc_compute_api(client, auth_headers):
    resp = client.post(
        "/api/quality/spc/compute",
        headers=auth_headers,
        json={
            "values": [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98, 1.0, 1.5],
            "chart_type": "I-MR",
            "usl": 1.3,
            "lsl": 0.7,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_count"] == 9
    assert data["status"] == "alert"
