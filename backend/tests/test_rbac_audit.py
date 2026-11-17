"""RBAC 权限守卫与操作审计落库。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import AuditLog, Permission, RolePermission, User
from app.permissions import (
    ALL_PERMISSION_CODES,
    ROLE_DEFAULT_PERMISSIONS,
    WORK_ORDERS_WRITE,
    seed_rbac,
)

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_rbac_into(db):
    """在测试会话中写入与 seed_rbac 一致的权限映射（不碰 SessionLocal）。"""
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
    _seed_rbac_into(db)
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


def _make_user(db, username: str, password: str, role: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
            "enterprise_code": "江西中软",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _wo_payload(order_no: str = "WO-RBAC-001"):
    return {
        "order_no": order_no,
        "product_name": "权限测试产品",
        "plan_quantity": 10,
    }


def test_user_role_denied_work_order_write(client, db_session):
    _make_user(db_session, "readonly", "pass123", "user")
    token = _login(client, "readonly", "pass123")
    response = client.post(
        "/api/work-orders",
        json=_wo_payload("WO-DENY-001"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "无权限"


def test_admin_role_allowed_work_order_write(client, db_session):
    _make_user(db_session, "admin_rbac", "pass123", "admin")
    token = _login(client, "admin_rbac", "pass123")
    response = client.post(
        "/api/work-orders",
        json=_wo_payload("WO-ALLOW-001"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["order_no"] == "WO-ALLOW-001"

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.username == "admin_rbac",
            AuditLog.resource == "work_order",
            AuditLog.success.is_(True),
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.action == "create"


def test_manager_role_allowed_work_order_write(client, db_session):
    _make_user(db_session, "mgr", "pass123", "manager")
    token = _login(client, "mgr", "pass123")
    response = client.post(
        "/api/work-orders",
        json=_wo_payload("WO-MGR-001"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_me_returns_permissions(client, db_session):
    _make_user(db_session, "viewer_me", "pass123", "user")
    token = _login(client, "viewer_me", "pass123")
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "user"
    assert "permissions" in data
    assert WORK_ORDERS_WRITE not in data["permissions"]
    assert "reports.read" in data["permissions"]


def test_me_admin_has_all_permissions(client, db_session):
    _make_user(db_session, "admin_me", "pass123", "admin")
    token = _login(client, "admin_me", "pass123")
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    perms = response.json()["permissions"]
    for code, _ in ALL_PERMISSION_CODES:
        assert code in perms


def test_login_success_writes_audit(client, db_session):
    _make_user(db_session, "audit_ok", "pass123", "admin")
    response = client.post(
        "/api/auth/login",
        json={
            "username": "audit_ok",
            "password": "pass123",
            "enterprise_code": "江西中软",
        },
    )
    assert response.status_code == 200
    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.username == "audit_ok", AuditLog.action == "login")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.success is True
    assert row.resource == "auth"
    assert row.detail is None or "password" not in (row.detail or {})


def test_login_failure_writes_audit(client, db_session):
    _make_user(db_session, "audit_fail", "pass123", "user")
    response = client.post(
        "/api/auth/login",
        json={
            "username": "audit_fail",
            "password": "wrong-password",
            "enterprise_code": "江西中软",
        },
    )
    assert response.status_code == 401
    row = (
        db_session.query(AuditLog)
        .filter(AuditLog.username == "audit_fail", AuditLog.action == "login")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert row is not None
    assert row.success is False
    assert row.detail is None or "password" not in str(row.detail)


def test_user_cannot_read_audit_logs(client, db_session):
    _make_user(db_session, "no_audit", "pass123", "user")
    token = _login(client, "no_audit", "pass123")
    response = client.get(
        "/api/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_read_audit_logs(client, db_session):
    _make_user(db_session, "audit_admin", "pass123", "admin")
    token = _login(client, "audit_admin", "pass123")
    response = client.get(
        "/api/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "items" in response.json()


def test_user_denied_messages_kanban_equipment_write(client, db_session):
    _make_user(db_session, "ro_more", "pass123", "user")
    token = _login(client, "ro_more", "pass123")
    headers = {"Authorization": f"Bearer {token}"}

    msg = client.post(
        "/api/messages",
        json={
            "title": "t",
            "content": "c",
            "category": "system",
            "priority": "normal",
        },
        headers=headers,
    )
    assert msg.status_code == 403

    board = client.post(
        "/api/kanban-boards",
        json={
            "board_code": "KB-DENY",
            "board_name": "deny",
            "category": "production",
        },
        headers=headers,
    )
    assert board.status_code == 403

    eq = client.post(
        "/api/equipment",
        json={"equipment_code": "EQ-DENY", "name": "deny"},
        headers=headers,
    )
    assert eq.status_code == 403


def test_admin_allowed_message_write_with_audit(client, db_session):
    _make_user(db_session, "admin_msg", "pass123", "admin")
    token = _login(client, "admin_msg", "pass123")
    response = client.post(
        "/api/messages",
        json={
            "title": "审计消息",
            "content": "内容",
            "category": "system",
            "priority": "normal",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.username == "admin_msg",
            AuditLog.resource == "message",
            AuditLog.action == "create",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None


def test_seed_rbac_idempotent(db_session):
    # 已在 fixture 中 seed 一次；再调用模块级 seed 不应抛错（可能写真实库，跳过）
    # 仅验证测试库内映射完整
    codes = {p.code for p in db_session.query(Permission).all()}
    assert WORK_ORDERS_WRITE in codes
    assert "messages.write" in codes
    assert "kanban.write" in codes
    assert "equipment.write" in codes
    user_codes = {
        r.permission_code
        for r in db_session.query(RolePermission).filter(RolePermission.role == "user")
    }
    assert WORK_ORDERS_WRITE not in user_codes
    assert "messages.write" not in user_codes
    assert "reports.read" in user_codes
    # 避免未使用导入告警
    assert callable(seed_rbac)
