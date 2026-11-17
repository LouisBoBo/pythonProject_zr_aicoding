"""工作台 R02：四张汇总卡 + 待办筛选/完成。"""

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import (
    DashboardTodo,
    InventoryStock,
    Material,
    Message,
    QualityAnomaly,
    User,
    Warehouse,
    WorkOrder,
)

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
            username="wb_user",
            hashed_password=hash_password("pass123"),
            role="admin",
        )
    )
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "wb_user",
            "password": "pass123",
            "enterprise_code": "前海中软",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_data(db_session):
    today = date.today()
    db_session.add_all(
        [
            WorkOrder(
                order_no="WO-OD-1",
                product_name="逾期产品",
                plan_quantity=10,
                status="in_progress",
                end_date=today - timedelta(days=2),
            ),
            WorkOrder(
                order_no="WO-OK-1",
                product_name="未逾期",
                plan_quantity=10,
                status="pending",
                end_date=today + timedelta(days=2),
            ),
            Message(
                title="未读1",
                content="c",
                category="system",
                is_read=False,
            ),
            Message(
                title="已读",
                content="c",
                category="system",
                is_read=True,
            ),
            QualityAnomaly(
                production_line="A",
                process="贴片",
                defect_type="虚焊",
                status="open",
            ),
            QualityAnomaly(
                production_line="A",
                process="贴片",
                defect_type="短路",
                status="closed",
            ),
        ]
    )
    wh = Warehouse(code="WH1", name="主仓")
    mat = Material(material_code="M1", material_name="物料1", safety_stock=20)
    db_session.add_all([wh, mat])
    db_session.flush()
    db_session.add(
        InventoryStock(
            material_id=mat.id,
            material_code=mat.material_code,
            material_name=mat.material_name,
            warehouse_id=wh.id,
            warehouse_name=wh.name,
            quantity=5,
            safety_stock=20,
            unit="件",
        )
    )
    # material_id FK may require Material - check if FK enforced
    db_session.add_all(
        [
            DashboardTodo(
                type="work_order",
                title="跟进逾期工单",
                description="d1",
                priority="high",
                link="/work-orders/overdue",
                status="open",
                created_at=datetime.utcnow(),
            ),
            DashboardTodo(
                type="quality",
                title="复核异常",
                description="d2",
                priority="medium",
                link="/quality",
                status="open",
                created_at=datetime.utcnow(),
            ),
            DashboardTodo(
                type="inventory",
                title="已完成待办",
                description="d3",
                priority="low",
                link="/warehouse/low-stock",
                status="done",
                created_at=datetime.utcnow(),
            ),
        ]
    )
    db_session.commit()


def test_workbench_requires_auth(client):
    assert client.get("/api/dashboard/workbench").status_code == 403


def test_workbench_summary_cards(client, auth_headers, sample_data):
    resp = client.get("/api/dashboard/workbench", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    cards = {c["key"]: c for c in data["cards"]}
    assert cards["overdue_work_orders"]["value"] == 1
    assert cards["overdue_work_orders"]["link"] == "/work-orders/overdue"
    assert cards["unread_messages"]["value"] == 1
    assert cards["unread_messages"]["link"] == "/messages"
    assert cards["open_quality_anomalies"]["value"] == 1
    assert cards["low_stock_alerts"]["value"] == 1
    assert cards["low_stock_alerts"]["link"] == "/warehouse/low-stock"
    # 默认只返回 open 待办
    assert len(data["todos"]) == 2
    assert all(t["status"] == "open" for t in data["todos"])


def test_workbench_todo_type_filter(client, auth_headers, sample_data):
    resp = client.get(
        "/api/dashboard/workbench?todo_type=quality",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    todos = resp.json()["todos"]
    assert len(todos) == 1
    assert todos[0]["type"] == "quality"


def test_complete_todo(client, auth_headers, sample_data, db_session):
    open_todo = (
        db_session.query(DashboardTodo)
        .filter(DashboardTodo.status == "open")
        .first()
    )
    resp = client.patch(
        f"/api/dashboard/todos/{open_todo.id}/complete",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    again = client.patch(
        f"/api/dashboard/todos/{open_todo.id}/complete",
        headers=auth_headers,
    )
    assert again.status_code == 200
    assert again.json()["status"] == "done"

    listed = client.get("/api/dashboard/workbench", headers=auth_headers)
    assert all(t["id"] != open_todo.id for t in listed.json()["todos"])
