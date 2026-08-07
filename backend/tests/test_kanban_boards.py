import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User

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
def test_user(db_session):
    user = User(
        username="testuser",
        hashed_password=hash_password("password123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _get_token(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "password123",
            "enterprise_code": "江西中软",
        },
    )
    return response.json()["access_token"]


def _board_payload(board_code="KB20250807001", **overrides):
    payload = {
        "board_code": board_code,
        "board_name": "生产监控看板",
        "category": "production",
        "production_line": "A线",
        "owner": "张三",
        "description": "A线生产实时监控",
        "refresh_interval": 30,
        "remark": "测试备注",
    }
    payload.update(overrides)
    return payload


def test_create_kanban_board_without_token(client):
    response = client.post(
        "/api/kanban-boards",
        json=_board_payload(),
    )
    assert response.status_code == 403


def test_create_and_list_kanban_boards(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(category="quality"),
        headers=headers,
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["board_code"] == "KB20250807001"
    assert data["board_name"] == "生产监控看板"
    assert data["category"] == "quality"
    assert data["status"] == "draft"
    assert data["refresh_interval"] == 30

    list_response = client.get("/api/kanban-boards", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["board_code"] == data["board_code"]


def test_create_kanban_board_minimal_fields(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/kanban-boards",
        json={
            "board_code": "KB-MIN-001",
            "board_name": "最小字段看板",
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["board_code"] == "KB-MIN-001"
    assert data["status"] == "draft"
    assert data["category"] == "production"
    assert data["refresh_interval"] == 60


def test_duplicate_board_code_returns_409(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}
    payload = _board_payload(board_code="KB-DUP-001")

    first = client.post("/api/kanban-boards", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post("/api/kanban-boards", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"] == "看板编码已存在"


def test_list_kanban_boards_filter_by_status(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-FILTER-001"),
        headers=headers,
    )

    draft_response = client.get("/api/kanban-boards?status=draft", headers=headers)
    assert draft_response.status_code == 200
    assert draft_response.json()["total"] == 1

    active_response = client.get("/api/kanban-boards?status=active", headers=headers)
    assert active_response.status_code == 200
    assert active_response.json()["total"] == 0


def test_list_kanban_boards_filter_by_category(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-CAT-001", category="equipment"),
        headers=headers,
    )
    client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-CAT-002", category="warehouse"),
        headers=headers,
    )

    equipment_response = client.get("/api/kanban-boards?category=equipment", headers=headers)
    assert equipment_response.status_code == 200
    assert equipment_response.json()["total"] == 1
    assert equipment_response.json()["items"][0]["board_code"] == "KB-CAT-001"


def test_get_kanban_board_detail(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-DETAIL-001"),
        headers=headers,
    )
    board_id = create_response.json()["id"]

    detail_response = client.get(f"/api/kanban-boards/{board_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["board_code"] == "KB-DETAIL-001"

    not_found = client.get("/api/kanban-boards/9999", headers=headers)
    assert not_found.status_code == 404


def test_update_kanban_board(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-UPD-001"),
        headers=headers,
    )
    board_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/kanban-boards/{board_id}",
        json={"board_name": "更新后的看板", "refresh_interval": 120},
        headers=headers,
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["board_name"] == "更新后的看板"
    assert data["refresh_interval"] == 120


def test_kanban_board_status_transitions(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-STATUS-001"),
        headers=headers,
    )
    board_id = create_response.json()["id"]

    publish_response = client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "active"},
        headers=headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "active"

    archive_response = client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "archived"},
        headers=headers,
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    invalid_response = client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "draft"},
        headers=headers,
    )
    assert invalid_response.status_code == 400


def test_reactivate_kanban_board(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-REACT-001"),
        headers=headers,
    )
    board_id = create_response.json()["id"]

    client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "active"},
        headers=headers,
    )
    client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "archived"},
        headers=headers,
    )

    reactivate_response = client.patch(
        f"/api/kanban-boards/{board_id}/status",
        json={"status": "active"},
        headers=headers,
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["status"] == "active"


def test_delete_kanban_board(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-DEL-001"),
        headers=headers,
    )
    board_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/kanban-boards/{board_id}", headers=headers)
    assert delete_response.status_code == 204

    detail_response = client.get(f"/api/kanban-boards/{board_id}", headers=headers)
    assert detail_response.status_code == 404


def test_list_kanban_boards_search(client, test_user):
    token = _get_token(client, test_user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-SEARCH-001", board_name="特殊看板A"),
        headers=headers,
    )
    client.post(
        "/api/kanban-boards",
        json=_board_payload(board_code="KB-OTHER-002", board_name="普通看板B"),
        headers=headers,
    )

    search_response = client.get("/api/kanban-boards?board_name=特殊", headers=headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1
    assert search_response.json()["items"][0]["board_code"] == "KB-SEARCH-001"
