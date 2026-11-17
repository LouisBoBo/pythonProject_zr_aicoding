import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.material_purchase import purchase_profile_for
from app.models import Material, User

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
            username="buyer",
            hashed_password=hash_password("password123"),
            role="user",
        )
    )
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "buyer",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_material_purchase_list_includes_supplier_and_price(client, db_session, auth_headers):
    profile = purchase_profile_for("IC-STM32F407")
    db_session.add(
        Material(
            material_code="IC-STM32F407",
            material_name="STM32F407VET6",
            category="芯片",
            spec="LQFP-100",
            unit="片",
            **profile,
        )
    )
    db_session.commit()

    resp = client.get("/api/material-purchases?material_code=STM32", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["supplier_name"] == "上海意法半导体有限公司"
    assert item["supplier_contact"] == "赵衡"
    assert item["supplier_phone"] == "021-61328000"
    assert item["supplier_address"] == "上海市浦东新区张江高科技园区祖冲之路2288号"
    assert item["purchase_price"] == 26.8


def test_material_purchase_list_requires_auth(client):
    resp = client.get("/api/material-purchases")
    assert resp.status_code in (401, 403)
