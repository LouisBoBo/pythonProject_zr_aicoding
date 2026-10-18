"""R06：本人改密 + admin 用户管理。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Permission, RolePermission, User
from app.permissions import ALL_PERMISSION_CODES, ROLE_DEFAULT_PERMISSIONS, SETTINGS_ADMIN

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_rbac(db):
    existing = {p.code for p in db.query(Permission).all()}
    for code, name in ALL_PERMISSION_CODES:
        if code not in existing:
            db.add(Permission(code=code, name=name))
    db.flush()
    for role, codes in ROLE_DEFAULT_PERMISSIONS.items():
        for code in codes:
            exists = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role == role,
                    RolePermission.permission_code == code,
                )
                .first()
            )
            if not exists:
                db.add(RolePermission(role=role, permission_code=code))
    db.commit()


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    _seed_rbac(db)
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


def _make_user(db, username, password, role):
    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username, password):
    resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
            "enterprise_code": "前海中软",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_change_password_requires_old_password(client, db_session):
    _make_user(db_session, "alice", "oldpass1", "user")
    token = _login(client, "alice", "oldpass1")
    headers = {"Authorization": f"Bearer {token}"}

    bad = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "wrong", "new_password": "newpass12"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "oldpass1", "new_password": "newpass12"},
    )
    assert ok.status_code == 200

    assert client.post(
        "/api/auth/login",
        json={
            "username": "alice",
            "password": "oldpass1",
            "enterprise_code": "前海中软",
        },
    ).status_code == 401
    assert _login(client, "alice", "newpass12")


def test_user_cannot_manage_users(client, db_session):
    _make_user(db_session, "bob", "pass1234", "user")
    token = _login(client, "bob", "pass1234")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/users", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/users",
            headers=headers,
            json={"username": "x", "password": "pass1234", "role": "user"},
        ).status_code
        == 403
    )


def test_admin_create_user_and_reset_password(client, db_session):
    admin = _make_user(db_session, "root", "admin123", "admin")
    token = _login(client, "root", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api/users",
        headers=headers,
        json={"username": "newbie", "password": "init1234", "role": "manager"},
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert created.json()["role"] == "manager"

    dup = client.post(
        "/api/users",
        headers=headers,
        json={"username": "newbie", "password": "init1234", "role": "user"},
    )
    assert dup.status_code == 409

    reset = client.post(
        f"/api/users/{user_id}/reset-password",
        headers=headers,
        json={"new_password": "reset999"},
    )
    assert reset.status_code == 200
    assert _login(client, "newbie", "reset999")

    # 至少保留一名 admin：禁止把唯一 admin 改成非 admin
    demote = client.patch(
        f"/api/users/{admin.id}",
        headers=headers,
        json={"role": "user"},
    )
    assert demote.status_code == 400

    listed = client.get("/api/users", headers=headers)
    assert listed.status_code == 200
    names = {u["username"] for u in listed.json()["items"]}
    assert "root" in names and "newbie" in names
    assert SETTINGS_ADMIN  # 确保常量仍被引用
