"""R07 顶栏全局搜索：短关键字空结果、工单号可命中、各组最多 5 条。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Equipment, Material, User, WorkOrder

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
            username="search_user",
            hashed_password=hash_password("pass123"),
            role="admin",
        )
    )
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "search_user",
            "password": "pass123",
            "enterprise_code": "前海中软",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed(db_session):
    db_session.add(
        WorkOrder(
            order_no="WO-SEARCH-001",
            product_name="测试产品A",
            product_code="P-A",
            plan_quantity=10,
            actual_quantity=0,
            status="pending",
            priority="normal",
        )
    )
    db_session.add(
        Equipment(
            equipment_code="EQ-SEARCH-01",
            name="冲压机A",
            status="运行",
        )
    )
    db_session.add(
        Material(
            material_code="MAT-SEARCH-01",
            material_name="钢板A",
            category="原材料",
            unit="件",
        )
    )
    db_session.commit()


def test_short_keyword_returns_empty(client, auth_headers, db_session):
    _seed(db_session)
    resp = client.get("/api/search", params={"q": "W"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["work_orders"] == []
    assert data["equipment"] == []
    assert data["materials"] == []


def test_order_no_hit(client, auth_headers, db_session):
    _seed(db_session)
    resp = client.get("/api/search", params={"q": "WO-SEARCH"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["work_orders"]) == 1
    assert data["work_orders"][0]["order_no"] == "WO-SEARCH-001"
    assert data["equipment"] == []
    assert data["materials"] == []


def test_equipment_and_material_hit(client, auth_headers, db_session):
    _seed(db_session)
    eq = client.get("/api/search", params={"q": "EQ-SEARCH"}, headers=auth_headers)
    assert eq.status_code == 200
    assert len(eq.json()["equipment"]) == 1
    assert eq.json()["equipment"][0]["equipment_code"] == "EQ-SEARCH-01"

    mat = client.get("/api/search", params={"q": "MAT-SEARCH"}, headers=auth_headers)
    assert mat.status_code == 200
    assert len(mat.json()["materials"]) == 1
    assert mat.json()["materials"][0]["material_code"] == "MAT-SEARCH-01"


def test_limit_five_per_group(client, auth_headers, db_session):
    for i in range(7):
        db_session.add(
            WorkOrder(
                order_no=f"WO-LIM-{i:02d}",
                product_name=f"限流产品{i}",
                plan_quantity=1,
                actual_quantity=0,
                status="pending",
                priority="normal",
            )
        )
    db_session.commit()
    resp = client.get("/api/search", params={"q": "WO-LIM"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["work_orders"]) == 5
