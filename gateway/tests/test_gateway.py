"""Gateway behaviour: MES-backed login, alias routing, byte-exact streaming, and error mapping."""

from __future__ import annotations

import json
import sqlite3
import time

import httpx
import pytest
from zr_gateway import auth
from zr_gateway.app import create_app
from zr_gateway.config import (
    ConfigError,
    Provider,
    ModelRoute,
    Settings,
    load_settings,
    mask_key,
    parse_catalog,
    parse_model_map,
    parse_upstream_base_url,
)
from zr_gateway.mes_login import MesLogin, MesUnavailable
from zr_gateway.store import Session, Store
from zr_gateway.upstream import Upstream, UpstreamUnavailable

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


STREAM_CHUNKS = [
    b'data: {"choices":[{"delta":{"reasoning_content":"think"},"index":0}]}\n\n',
    b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"db","arguments":"{\\"sql"}}]},"index":0}]}\n\n',
    b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls","index":0}]}\n\n',
    b'data: {"choices":[],"usage":{"prompt_tokens":120,"completion_tokens":45}}\n\n',
    b"data: [DONE]\n\n",
]


def settings_for(tmp_path, **overrides) -> Settings:
    values = {
        "upstream_base_url": "https://upstream.test/v1",
        "upstream_key": "sk-upstream-secret",
        "model_map": {"standard": "deepseek-chat", "deep": "deepseek-reasoner"},
        "db_path": str(tmp_path / "gateway.sqlite3"),
        "token_ttl_seconds": 3600,
        "upstream_timeout_seconds": 30.0,
        "mes_base_url": "http://127.0.0.1:8009",
        "mes_timeout_seconds": 5.0,
        "force_include_usage": True,
    }
    values.update(overrides)
    return Settings(**values)


KEY_A = "sk-aaaa1111bbbb2222cccc"
KEY_B = "sk-dddd3333eeee4444ffff"


def catalog_settings(tmp_path, admin_token: str = "") -> Settings:
    """Two providers so attribution bugs cannot hide behind a single upstream."""
    providers = (
        Provider(id="deepseek-official", display_name="DeepSeek 官方", base_url="https://upstream.test/v1", key=KEY_A),
        Provider(id="vendor-b", display_name="备用供应商", base_url="https://vendor.test/v1", key=KEY_B),
    )
    models = (
        ModelRoute(alias="standard", display_name="标准", provider_id="deepseek-official", real_name="deepseek-v4-flash"),
        ModelRoute(alias="deep", display_name="深度", provider_id="deepseek-official", real_name="deepseek-reasoner"),
        ModelRoute(alias="code", display_name="编码", provider_id="vendor-b", real_name="vendor-code-1", purpose="code"),
    )
    return Settings(
        upstream_base_url=providers[0].base_url,
        upstream_key=providers[0].key,
        model_map={item.alias: item.real_name for item in models},
        db_path=str(tmp_path / "gateway.sqlite3"),
        token_ttl_seconds=3600,
        upstream_timeout_seconds=30.0,
        mes_base_url="http://127.0.0.1:8009",
        mes_timeout_seconds=5.0,
        force_include_usage=True,
        providers=providers,
        models=models,
        admin_token=admin_token,
    )


class FakeResponse:
    def __init__(self, status_code: int = 200, chunks: list[bytes] | None = None, body: bytes = b"", headers: dict | None = None):
        self.status_code = status_code
        self._chunks = list(chunks or [])
        self._body = body
        self.headers = headers or {"content-type": "application/json"}
        self.closed = False

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    async def aread(self) -> bytes:
        return self._body

    async def aclose(self) -> None:
        self.closed = True


class FakeUpstream:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.closed = False

    async def send_chat(self, payload: dict, request_id: str, provider=None) -> FakeResponse:
        self.calls.append({"payload": payload, "request_id": request_id, "provider": provider})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        self.closed = True


class FakeMes:
    """Stands in for the MES login endpoint without touching the MES service."""

    def __init__(self, accepted: bool = True, error: Exception | None = None):
        self._accepted = accepted
        self._error = error
        self.calls: list[dict] = []
        self.closed = False

    async def verify(self, username: str, password: str, request_id: str) -> bool:
        self.calls.append({"username": username, "password": password, "request_id": request_id})
        if self._error is not None:
            raise self._error
        return self._accepted

    async def aclose(self) -> None:
        self.closed = True


def build(tmp_path, responses: list, mes: FakeMes | None = None, settings: Settings | None = None):
    resolved = settings if settings is not None else settings_for(tmp_path)
    store = Store(resolved.db_path)
    upstream = FakeUpstream(responses)
    mes_client = mes if mes is not None else FakeMes()
    return create_app(resolved, store=store, upstream=upstream, mes=mes_client), store, upstream, mes_client, resolved


async def login(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/login",
        json={"enterprise": " jiangxi ", "username": "louis", "password": "correct-horse"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def usage_rows(store: Store) -> list[sqlite3.Row]:
    with sqlite3.connect(store.path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute("SELECT * FROM usage_records ORDER BY id").fetchall()


def store_session(username: str = "louis") -> Session:
    return Session(username=username, enterprise="jiangxi", expires_at=int(time.time()) + 3600)


# --- login -----------------------------------------------------------------


async def test_login_returns_contract_and_stores_only_the_digest(tmp_path) -> None:
    app, store, _upstream, mes, _settings = build(tmp_path, [])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        response = await client.post(
            "/api/login",
            json={"enterprise": " Jiangxi ", "username": "louis", "password": "correct-horse"},
        )
    body = response.json()
    assert response.status_code == 200
    assert set(body) == {"token", "expiresAt", "user", "models"}
    assert body["user"] == {"name": "louis"}
    assert body["expiresAt"] > int(time.time() * 1000)
    assert [item["alias"] for item in body["models"]] == ["standard", "deep"]
    assert mes.calls == [{"username": "louis", "password": "correct-horse", "request_id": body["token"] and mes.calls[0]["request_id"]}]

    with sqlite3.connect(store.path) as connection:
        rows = connection.execute("SELECT token_digest, username, enterprise FROM sessions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == auth.token_digest(body["token"])
    assert body["token"] not in rows[0][0]
    assert (rows[0][1], rows[0][2]) == ("louis", "jiangxi")


async def test_mes_rejection_is_a_plain_401(tmp_path) -> None:
    app, _store, _upstream, _mes, _settings = build(tmp_path, [], mes=FakeMes(accepted=False))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        rejected = await client.post("/api/login", json={"username": "louis", "password": "wrong-horse"})
        empty = await client.post("/api/login", json={"username": " ", "password": ""})
        overlong = await client.post("/api/login", json={"username": "louis", "password": "x" * 300})
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "invalid_credentials"
    assert empty.status_code == 400
    assert overlong.status_code == 401


async def test_mes_outage_is_reported_as_502(tmp_path) -> None:
    app, _store, _upstream, _mes, _settings = build(tmp_path, [], mes=FakeMes(error=MesUnavailable("connect refused")))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        response = await client.post("/api/login", json={"username": "louis", "password": "correct-horse"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "login_unavailable"


async def test_invalid_enterprise_is_rejected_before_mes(tmp_path) -> None:
    app, _store, _upstream, mes, _settings = build(tmp_path, [])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        response = await client.post(
            "/api/login",
            json={"enterprise": "../etc", "username": "louis", "password": "correct-horse"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_enterprise"
    assert mes.calls == []


# --- chat authorization and routing ---------------------------------------


async def test_chat_requires_a_live_bearer_token(tmp_path) -> None:
    app, store, upstream, _mes, _settings = build(tmp_path, [])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        missing = await client.post("/v1/chat/completions", json={"model": "standard", "messages": []})
        token = await login(client)
        assert store.revoke_sessions("louis") == 1
        revoked = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "messages": []},
        )
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "session_expired"
    assert revoked.status_code == 401
    assert upstream.calls == []


async def test_unknown_alias_is_rejected_before_the_upstream(tmp_path) -> None:
    app, _store, upstream, _mes, _settings = build(tmp_path, [])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        response = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "deepseek-chat", "messages": []},
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "model_not_allowed"
    assert upstream.calls == []


async def test_stream_is_forwarded_byte_for_byte_with_the_real_model(tmp_path) -> None:
    response = FakeResponse(chunks=STREAM_CHUNKS)
    app, store, upstream, _mes, _settings = build(tmp_path, [response])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "deep", "stream": True, "messages": [{"role": "user", "content": "查数"}]},
        ) as result:
            assert result.status_code == 200
            assert result.headers["content-type"].startswith("text/event-stream")
            forwarded = b"".join([chunk async for chunk in result.aiter_bytes()])

    assert forwarded == b"".join(STREAM_CHUNKS)
    assert response.closed
    sent = upstream.calls[0]["payload"]
    assert sent["model"] == "deepseek-reasoner"
    assert sent["stream_options"]["include_usage"] is True
    assert sent["messages"] == [{"role": "user", "content": "查数"}]

    rows = usage_rows(store)
    assert len(rows) == 1
    assert rows[0]["username"] == "louis"
    assert rows[0]["model_alias"] == "deep"
    assert rows[0]["real_name"] == "deepseek-reasoner"
    assert (rows[0]["input_tokens"], rows[0]["output_tokens"]) == (120, 45)
    assert rows[0]["status"] == "ok"


async def test_stream_options_from_the_client_are_kept(tmp_path) -> None:
    app, _store, upstream, _mes, _settings = build(tmp_path, [FakeResponse(chunks=[b"data: [DONE]\n\n"])])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        async with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "stream": True, "stream_options": {"include_usage": False}, "messages": []},
        ) as result:
            _ = [chunk async for chunk in result.aiter_bytes()]
    assert upstream.calls[0]["payload"]["stream_options"] == {"include_usage": True}


async def test_non_stream_reply_is_passed_through_and_counted(tmp_path) -> None:
    body = b'{"id":"x","choices":[{"message":{"content":"ok"}}],"usage":{"prompt_tokens":7,"completion_tokens":3}}'
    app, store, upstream, _mes, _settings = build(tmp_path, [FakeResponse(body=body)])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        result = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "messages": []},
        )
    assert result.status_code == 200
    assert result.content == body
    assert upstream.calls[0]["payload"]["model"] == "deepseek-chat"
    rows = usage_rows(store)
    assert (rows[0]["input_tokens"], rows[0]["output_tokens"]) == (7, 3)


# --- failure mapping ------------------------------------------------------


async def test_upstream_rate_limit_is_mapped_without_leaking_its_body(tmp_path) -> None:
    secret = b'{"error":{"message":"upstream detail sk-upstream-secret"}}'
    app, _store, _upstream, _mes, _settings = build(tmp_path, [FakeResponse(status_code=429, body=secret)])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        result = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "messages": []},
        )
    assert result.status_code == 429
    assert result.json()["error"]["code"] == "rate_limited"
    assert "sk-upstream-secret" not in result.text


async def test_unreachable_upstream_is_502(tmp_path) -> None:
    app, _store, _upstream, _mes, _settings = build(tmp_path, [UpstreamUnavailable("connection refused")])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        result = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "messages": []},
        )
    assert result.status_code == 502
    assert result.json()["error"]["code"] == "upstream_unavailable"


async def test_bad_json_is_rejected(tmp_path) -> None:
    app, _store, upstream, _mes, _settings = build(tmp_path, [])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        result = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
            content=b"{not json",
        )
    assert result.status_code == 400
    assert upstream.calls == []


# --- MES login client -----------------------------------------------------


def mes_backed(handler) -> MesLogin:
    settings = Settings(
        upstream_base_url="https://upstream.test",
        upstream_key="sk",
        model_map={"standard": "deepseek-chat"},
        db_path="unused.sqlite3",
        token_ttl_seconds=60,
        upstream_timeout_seconds=5.0,
        mes_base_url="http://127.0.0.1:8009",
        mes_timeout_seconds=5.0,
        force_include_usage=True,
    )
    client = MesLogin(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=settings.mes_base_url)
    return client


async def test_mes_client_contract() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        status = 200 if request.content and b"good-password" in request.content else 401
        return httpx.Response(status, json={"access_token": "mes-jwt"} if status == 200 else {"detail": "账号或密码错误"})

    client = mes_backed(handler)
    assert await client.verify("louis", "good-password", "req-9") is True
    assert await client.verify("louis", "bad-password", "req-9") is False
    assert str(seen[0].url) == "http://127.0.0.1:8009/api/auth/login"
    assert seen[0].headers["x-request-id"] == "req-9"
    await client.aclose()


async def test_mes_client_treats_server_errors_as_unavailable() -> None:
    client = mes_backed(lambda request: httpx.Response(500, text="boom"))
    with pytest.raises(MesUnavailable):
        await client.verify("louis", "correct-horse", "req-10")
    await client.aclose()


# --- upstream client ------------------------------------------------------


def transport_backed(settings, handler) -> Upstream:
    client = Upstream(settings)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


async def test_upstream_retries_once_before_the_first_byte(tmp_path) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"ok": True})

    upstream = transport_backed(settings_for(tmp_path), handler)
    response = await upstream.send_chat({"model": "deepseek-chat"}, "req-1")
    assert response.status_code == 200
    assert len(seen) == 2
    assert str(seen[0].url) == "https://upstream.test/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer sk-upstream-secret"
    assert seen[0].headers["x-request-id"] == "req-1"
    await response.aclose()
    await upstream.aclose()


async def test_upstream_gives_up_after_two_server_errors(tmp_path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, text="boom")

    upstream = transport_backed(settings_for(tmp_path), handler)
    with pytest.raises(UpstreamUnavailable):
        await upstream.send_chat({"model": "deepseek-chat"}, "req-2")
    assert calls == 2
    await upstream.aclose()


# --- settings -------------------------------------------------------------


def test_model_map_and_base_url_rules() -> None:
    assert parse_model_map("standard=deepseek-chat, deep = deepseek-reasoner") == {
        "standard": "deepseek-chat",
        "deep": "deepseek-reasoner",
    }
    with pytest.raises(ConfigError):
        parse_model_map("standard")
    assert parse_upstream_base_url("https://api.deepseek.com/") == "https://api.deepseek.com"
    assert parse_upstream_base_url("http://127.0.0.1:8000/v1") == "http://127.0.0.1:8000/v1"
    with pytest.raises(ConfigError):
        parse_upstream_base_url("http://api.deepseek.com")
    with pytest.raises(ConfigError):
        parse_upstream_base_url("https://user:pass@api.deepseek.com")


def test_settings_require_a_key_and_default_to_loopback_mes(tmp_path) -> None:
    with pytest.raises(ConfigError):
        load_settings({"ZR_GATEWAY_DB": str(tmp_path / "g.sqlite3")})
    settings = load_settings(
        {
            "ZR_GATEWAY_UPSTREAM_KEY": "sk-test",
            "ZR_GATEWAY_MODEL_MAP": "standard=deepseek-chat",
            "ZR_GATEWAY_DB": str(tmp_path / "g.sqlite3"),
        }
    )
    assert settings.model_map == {"standard": "deepseek-chat"}
    assert settings.upstream_base_url == "https://api.deepseek.com"
    assert settings.mes_base_url == "http://127.0.0.1:8009"


# --- provider/key/model catalog -------------------------------------------


def test_mask_key_shows_only_the_edges() -> None:
    assert mask_key(KEY_A) == "sk-aaaa1*****cccc"
    assert mask_key("short-key") == ""
    assert mask_key("") == ""


def catalog_document(**overrides) -> dict:
    document = {
        "providers": [
            {
                "id": "deepseek-official",
                "displayName": "DeepSeek 官方",
                "baseUrl": "https://api.deepseek.com",
                "keyEnv": "ZR_KEY_DEEPSEEK",
            }
        ],
        "models": [
            {"alias": "standard", "displayName": "标准", "provider": "deepseek-official", "model": "deepseek-chat"}
        ],
    }
    document.update(overrides)
    return document


def test_catalog_binds_every_alias_to_one_provider_and_model() -> None:
    providers, models = parse_catalog(catalog_document(), {"ZR_KEY_DEEPSEEK": KEY_A})
    assert [item.id for item in providers] == ["deepseek-official"]
    assert providers[0].key_hint == mask_key(KEY_A)
    assert [(item.alias, item.provider_id, item.real_name, item.purpose) for item in models] == [
        ("standard", "deepseek-official", "deepseek-chat", "llm")
    ]


@pytest.mark.parametrize(
    "document",
    [
        catalog_document(models=[{"alias": "standard", "provider": "nobody", "model": "deepseek-chat"}]),
        catalog_document(
            models=[
                {"alias": "standard", "provider": "deepseek-official", "model": "deepseek-chat"},
                {"alias": "standard", "provider": "deepseek-official", "model": "deepseek-reasoner"},
            ]
        ),
        catalog_document(models=[{"alias": "standard", "provider": "deepseek-official", "model": "deepseek-chat", "purpose": "chat"}]),
        catalog_document(models=[{"alias": "standard", "provider": "deepseek-official", "model": "deep seek"}]),
        catalog_document(
            providers=[{"id": "deepseek-official", "baseUrl": "http://api.deepseek.com", "keyEnv": "ZR_KEY_DEEPSEEK"}]
        ),
        catalog_document(
            providers=[{"id": "deepseek-official", "baseUrl": "https://api.deepseek.com", "key": KEY_A}]
        ),
        catalog_document(providers=[], models=[]),
    ],
)
def test_catalog_rejects_an_inconsistent_table(document) -> None:
    with pytest.raises(ConfigError):
        parse_catalog(document, {"ZR_KEY_DEEPSEEK": KEY_A})


def test_catalog_requires_the_key_in_the_environment() -> None:
    with pytest.raises(ConfigError):
        parse_catalog(catalog_document(), {})


def test_load_settings_reads_a_catalog_file(tmp_path) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog_document()), encoding="utf-8")
    settings = load_settings(
        {
            "ZR_GATEWAY_CATALOG": str(path),
            "ZR_KEY_DEEPSEEK": KEY_A,
            "ZR_GATEWAY_DB": str(tmp_path / "g.sqlite3"),
            "ZR_GATEWAY_ADMIN_TOKEN": "admin-token-123456",
        }
    )
    assert [item.id for item in settings.providers] == ["deepseek-official"]
    assert settings.route("standard").real_name == "deepseek-chat"
    assert settings.provider("deepseek-official").key_hint == mask_key(KEY_A)
    assert settings.admin_token == "admin-token-123456"

    with pytest.raises(ConfigError):
        load_settings(
            {
                "ZR_GATEWAY_CATALOG": str(path),
                "ZR_KEY_DEEPSEEK": KEY_A,
                "ZR_GATEWAY_DB": str(tmp_path / "g.sqlite3"),
                "ZR_GATEWAY_ADMIN_TOKEN": "too-short",
            }
        )


# --- per-provider attribution ---------------------------------------------


async def test_chat_uses_the_provider_bound_to_the_selected_alias(tmp_path) -> None:
    body = b'{"usage":{"prompt_tokens":5,"completion_tokens":2}}'
    app, store, upstream, _mes, _settings = build(
        tmp_path,
        [FakeResponse(body=body), FakeResponse(body=body)],
        settings=catalog_settings(tmp_path),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        first = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "standard", "messages": []},
        )
        second = await client.post(
            "/v1/chat/completions",
            headers={"authorization": f"Bearer {token}"},
            json={"model": "code", "messages": []},
        )
    assert (first.status_code, second.status_code) == (200, 200)
    assert upstream.calls[0]["provider"].id == "deepseek-official"
    assert upstream.calls[1]["provider"].id == "vendor-b"
    assert upstream.calls[1]["payload"]["model"] == "vendor-code-1"

    rows = usage_rows(store)
    assert (rows[0]["provider_id"], rows[0]["key_hint"], rows[0]["purpose"]) == (
        "deepseek-official",
        mask_key(KEY_A),
        "llm",
    )
    assert (rows[1]["provider_id"], rows[1]["key_hint"], rows[1]["purpose"]) == ("vendor-b", mask_key(KEY_B), "code")


async def test_catalog_and_usage_only_ever_carry_masked_keys(tmp_path) -> None:
    body = b'{"usage":{"prompt_tokens":7,"completion_tokens":3}}'
    app, _store, _upstream, _mes, _settings = build(
        tmp_path,
        [FakeResponse(body=body)],
        settings=catalog_settings(tmp_path),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        login_response = await client.post(
            "/api/login",
            json={"enterprise": "jiangxi", "username": "louis", "password": "correct-horse"},
        )
        token = login_response.json()["token"]
        headers = {"authorization": f"Bearer {token}"}
        await client.post("/v1/chat/completions", headers=headers, json={"model": "standard", "messages": []})
        catalog = await client.get("/v1/catalog", headers=headers)
        usage = await client.get("/v1/usage/models", headers=headers)

    bodies = [login_response.text, catalog.text, usage.text]
    for text in bodies:
        assert KEY_A not in text
        assert KEY_B not in text

    entries = catalog.json()["models"]
    assert {item["alias"]: item["keyHint"] for item in entries}["code"] == mask_key(KEY_B)
    assert {item["alias"]: item["providerName"] for item in entries}["code"] == "备用供应商"

    models = usage.json()["models"]
    assert len(models) == 1
    assert models[0]["providerName"] == "DeepSeek 官方"
    assert models[0]["keyHint"] == mask_key(KEY_A)
    assert models[0]["model"] == "deepseek-v4-flash"
    assert (models[0]["calls"], models[0]["inputTokens"], models[0]["outputTokens"]) == (1, 7, 3)


async def test_usage_endpoint_is_scoped_to_the_caller(tmp_path) -> None:
    settings = catalog_settings(tmp_path)
    app, store, _upstream, _mes, _settings = build(tmp_path, [], settings=settings)
    store.record_usage(
        request_id="req-other",
        session=store_session("someone-else"),
        model_alias="code",
        real_name="vendor-code-1",
        provider_id="vendor-b",
        key_hint=mask_key(KEY_B),
        purpose="code",
        input_tokens=100,
        output_tokens=200,
        status="ok",
        latency_ms=1,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        usage = await client.get("/v1/usage/models", headers={"authorization": f"Bearer {token}"})
    assert usage.status_code == 200
    assert usage.json()["models"] == []


async def test_admin_usage_requires_the_admin_token(tmp_path) -> None:
    app, _store, _upstream, _mes, _settings = build(tmp_path, [], settings=catalog_settings(tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        disabled = await client.get("/v1/admin/usage/models", headers={"authorization": f"Bearer {token}"})
    assert disabled.status_code == 404


async def test_admin_usage_rejects_the_wrong_token_and_serves_the_right_one(tmp_path) -> None:
    admin_token = "admin-token-123456"
    settings = catalog_settings(tmp_path, admin_token=admin_token)
    app, store, _upstream, _mes, _settings = build(tmp_path, [], settings=settings)
    store.record_usage(
        request_id="req-other",
        session=store_session("someone-else"),
        model_alias="code",
        real_name="vendor-code-1",
        provider_id="vendor-b",
        key_hint=mask_key(KEY_B),
        purpose="code",
        input_tokens=100,
        output_tokens=200,
        status="ok",
        latency_ms=1,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        token = await login(client)
        missing = await client.get("/v1/admin/usage/models")
        wrong = await client.get("/v1/admin/usage/models", headers={"authorization": "Bearer nope"})
        user_token = await client.get("/v1/admin/usage/models", headers={"authorization": f"Bearer {token}"})
        allowed = await client.get("/v1/admin/usage/models", headers={"authorization": f"Bearer {admin_token}"})
        filtered = await client.get(
            "/v1/admin/usage/models",
            params={"username": "someone-else"},
            headers={"authorization": f"Bearer {admin_token}"},
        )
    assert (missing.status_code, wrong.status_code, user_token.status_code) == (401, 401, 401)
    assert allowed.status_code == 200
    assert allowed.json()["models"][0]["keyHint"] == mask_key(KEY_B)
    assert len(filtered.json()["models"]) == 1


def test_store_migrates_the_old_usage_table(tmp_path) -> None:
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE usage_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              request_id TEXT NOT NULL UNIQUE,
              username TEXT NOT NULL,
              enterprise TEXT NOT NULL,
              model_alias TEXT NOT NULL,
              real_name TEXT NOT NULL,
              input_tokens INTEGER NOT NULL DEFAULT 0,
              output_tokens INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'ok',
              latency_ms INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL
            );
            INSERT INTO usage_records
              (request_id, username, enterprise, model_alias, real_name, input_tokens, output_tokens, status, latency_ms, created_at)
            VALUES ('req-1', 'louis', 'jiangxi', 'standard', 'deepseek-chat', 1, 2, 'ok', 3, 1000);
            """
        )
    store = Store(path)
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(usage_records)")}
    assert {"provider_id", "key_hint", "purpose"} <= columns
    rows = store.aggregate_models(start=0, end=2000)
    assert [(row["provider"], row["keyHint"], row["calls"]) for row in rows] == [("", "", 1)]
