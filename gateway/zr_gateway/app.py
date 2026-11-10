"""HTTP surface: MES-backed login plus an OpenAI-compatible chat proxy."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import auth
from .config import ModelRoute, Provider, Settings
from .mes_login import MesLogin, MesUnavailable
from .store import DEFAULT_USAGE_WINDOW_SECONDS, Session, Store
from .upstream import Upstream, UpstreamUnavailable

logger = logging.getLogger("zr_gateway")


class LoginBody(BaseModel):
    """Fields the desktop card posts; the enterprise key is recorded on the session."""

    enterprise: str = ""
    username: str = ""
    password: str = ""


def _now_ms() -> int:
    return int(time.time() * 1000)


def _error(status: int, message: str, error_type: str, code: str, request_id: str) -> JSONResponse:
    """OpenAI-shaped error body. Upstream text and credentials never appear here."""
    return JSONResponse(
        {"error": {"message": message, "type": error_type, "code": code}},
        status_code=status,
        headers={"x-request-id": request_id, "cache-control": "no-store"},
    )


def _upstream_error(status: int, request_id: str) -> JSONResponse:
    if status == 402:
        return _error(402, "额度不足，请联系管理员", "insufficient_quota", "quota_exceeded", request_id)
    if status == 429:
        return _error(429, "请求过于频繁，请稍后重试", "rate_limit_error", "rate_limited", request_id)
    if status in (401, 403):
        return _error(502, "模型服务鉴权失败，请联系管理员", "api_error", "upstream_auth", request_id)
    if status == 400:
        return _error(400, "上游拒绝了该请求，请联系管理员并提供请求 ID", "invalid_request_error", "upstream_rejected", request_id)
    return _error(502, "模型服务异常，请稍后重试", "api_error", "upstream_error", request_id)


def _usage_counts(payload: Any) -> tuple[int, int]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return 0, 0

    def count(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    return count(usage.get("prompt_tokens")), count(usage.get("completion_tokens"))


def _consume_events(buffer: str) -> tuple[str, dict | None]:
    """@returns the unterminated tail and the last `usage` object seen in complete SSE lines."""
    usage: dict | None = None
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "" or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("usage"), dict):
            usage = event["usage"]
    return buffer, usage


def _bearer_token(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = value.strip()
    return token or None


def _int_param(request: Request, name: str, fallback: int) -> int:
    raw = request.query_params.get(name, "").strip()
    return fallback if raw == "" else int(raw)


def create_app(
    settings: Settings,
    store: Store | None = None,
    upstream: Upstream | None = None,
    mes: MesLogin | None = None,
) -> FastAPI:
    """@param store - override for tests. @param upstream - override for tests. @param mes - override for tests."""
    session_store = store if store is not None else Store(settings.db_path)
    upstream_client = upstream if upstream is not None else Upstream(settings)
    mes_client = mes if mes is not None else MesLogin(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await upstream_client.aclose()
        await mes_client.aclose()

    app = FastAPI(title="zr-gateway", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def authorize(request: Request) -> Session | None:
        token = _bearer_token(request)
        if token is None:
            return None
        return session_store.resolve_session(auth.token_digest(token))

    def provider_of(route: ModelRoute) -> Provider | None:
        return settings.provider(route.provider_id)

    def record(
        session: Session,
        request_id: str,
        route: ModelRoute,
        provider: Provider,
        usage: dict | None,
        status: str,
        started: float,
    ) -> None:
        input_tokens, output_tokens = _usage_counts({"usage": usage})
        try:
            session_store.record_usage(
                request_id=request_id,
                session=session,
                model_alias=route.alias,
                real_name=route.real_name,
                provider_id=provider.id,
                key_hint=provider.key_hint,
                purpose=route.purpose,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status=status,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as error:  # accounting must never break a reply
            logger.warning("usage record failed request_id=%s error=%s", request_id, error)

    @app.get("/healthz")
    async def healthz() -> dict[str, bool]:
        return {"ok": True}

    def model_entries() -> list[dict]:
        """Client-visible catalog: alias, display name, provider, masked key. Never the key itself."""
        entries: list[dict] = []
        for route in settings.routes:
            provider = provider_of(route)
            if provider is None:
                continue
            entries.append(
                {
                    "alias": route.alias,
                    "displayName": route.display_name,
                    "provider": provider.id,
                    "providerName": provider.display_name,
                    "keyHint": provider.key_hint,
                    "purpose": route.purpose,
                    "model": route.real_name,
                }
            )
        return entries

    @app.post("/api/login")
    async def login(body: LoginBody) -> Response:
        request_id = uuid.uuid4().hex
        username = body.username.strip()
        password = body.password
        if username == "" or password == "":
            return _error(400, "请输入账号和密码", "invalid_request_error", "empty_credentials", request_id)
        if len(username) > 50 or len(password) > auth.MAX_CREDENTIAL_LENGTH:
            return _error(401, "用户名或密码错误", "invalid_credentials", "invalid_credentials", request_id)
        try:
            enterprise = auth.normalize_enterprise(body.enterprise)
        except ValueError:
            return _error(400, "企业编码无效", "invalid_request_error", "invalid_enterprise", request_id)
        try:
            accepted = await mes_client.verify(username, password, request_id)
        except MesUnavailable as error:
            logger.warning("mes login unavailable request_id=%s error=%s", request_id, error)
            return _error(502, "登录服务暂时不可用，请稍后重试", "api_error", "login_unavailable", request_id)
        if not accepted:
            logger.info("login rejected request_id=%s user=%s", request_id, username)
            return _error(401, "用户名或密码错误", "invalid_credentials", "invalid_credentials", request_id)
        token = auth.new_token()
        expires_at = _now_ms() + settings.token_ttl_seconds * 1000
        session_store.create_session(auth.token_digest(token), username, enterprise, expires_at)
        logger.info("login ok request_id=%s user=%s enterprise=%s", request_id, username, enterprise)
        return JSONResponse(
            {
                "token": token,
                "expiresAt": expires_at,
                "user": {"name": username},
                "models": [
                    {"hint": "", **entry}
                    for entry in model_entries()
                ],
            },
            headers={"x-request-id": request_id, "cache-control": "no-store"},
        )

    @app.get("/v1/models")
    async def models(request: Request) -> Response:
        request_id = uuid.uuid4().hex
        if authorize(request) is None:
            return _error(401, "登录已过期，请重新登录", "invalid_request_error", "session_expired", request_id)
        return JSONResponse(
            {
                "object": "list",
                "data": [
                    {"id": route.alias, "object": "model", "created": 0, "owned_by": route.provider_id}
                    for route in settings.routes
                ],
            },
            headers={"x-request-id": request_id},
        )

    @app.post("/v1/chat/completions")
    async def chat(request: Request) -> Response:
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        session = authorize(request)
        if session is None:
            return _error(401, "登录已过期，请重新登录", "invalid_request_error", "session_expired", request_id)
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error(400, "请求体不是合法 JSON", "invalid_request_error", "invalid_body", request_id)
        if not isinstance(payload, dict):
            return _error(400, "请求体必须是对象", "invalid_request_error", "invalid_body", request_id)
        alias = payload.get("model")
        route = settings.route(alias) if isinstance(alias, str) else None
        if route is None:
            return _error(403, "模型不在授权范围", "permission_error", "model_not_allowed", request_id)
        provider = provider_of(route)
        if provider is None:
            logger.error("catalog has no provider for alias=%s provider=%s", route.alias, route.provider_id)
            return _error(502, "模型网关配置有误，请联系管理员", "api_error", "upstream_unavailable", request_id)
        upstream_payload = {**payload, "model": route.real_name}
        streaming = bool(payload.get("stream"))
        if streaming and settings.force_include_usage:
            options = upstream_payload.get("stream_options")
            upstream_payload["stream_options"] = {
                **(options if isinstance(options, dict) else {}),
                "include_usage": True,
            }

        try:
            upstream_response = await upstream_client.send_chat(upstream_payload, request_id, provider)
        except UpstreamUnavailable as error:
            logger.warning("upstream unavailable request_id=%s provider=%s error=%s", request_id, provider.id, error)
            return _error(502, "模型服务暂不可用，请稍后重试", "api_error", "upstream_unavailable", request_id)

        if upstream_response.status_code >= 400:
            body = await upstream_response.aread()
            await upstream_response.aclose()
            logger.warning(
                "upstream rejected request_id=%s status=%s body=%s",
                request_id,
                upstream_response.status_code,
                body[:500].decode("utf-8", "replace"),
            )
            return _upstream_error(upstream_response.status_code, request_id)

        if not streaming:
            raw = await upstream_response.aread()
            await upstream_response.aclose()
            try:
                parsed: Any = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            record(session, request_id, route, provider, parsed.get("usage") if isinstance(parsed, dict) else None, "ok", started)
            return Response(
                content=raw,
                media_type=upstream_response.headers.get("content-type", "application/json"),
                headers={"x-request-id": request_id},
            )

        return StreamingResponse(
            _relay(upstream_response, session, request_id, route, provider, started),
            media_type="text/event-stream",
            headers={
                "x-request-id": request_id,
                "cache-control": "no-cache, no-transform",
                "x-accel-buffering": "no",
            },
        )

    async def _relay(
        response: httpx.Response,
        session: Session,
        request_id: str,
        route: ModelRoute,
        provider: Provider,
        started: float,
    ) -> AsyncIterator[bytes]:
        """Forward upstream bytes unchanged and account for usage without buffering the answer."""
        buffer = ""
        usage: dict | None = None
        status = "ok"
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
                buffer, seen = _consume_events(buffer + chunk.decode("utf-8", "replace"))
                if seen is not None:
                    usage = seen
        except asyncio.CancelledError:
            status = "aborted"
            raise
        except httpx.HTTPError as error:
            status = "upstream_error"
            logger.warning("stream interrupted request_id=%s error=%s", request_id, error)
            raise
        finally:
            try:
                await response.aclose()
            except Exception:  # the client may already be gone; closing is best effort
                pass
            record(session, request_id, route, provider, usage, status, started)

    @app.get("/v1/catalog")
    async def catalog(request: Request) -> Response:
        """Masked provider/model table for the client's model picker and usage page."""
        request_id = uuid.uuid4().hex
        if authorize(request) is None:
            return _error(401, "登录已过期，请重新登录", "invalid_request_error", "session_expired", request_id)
        providers: dict[str, Provider] = {}
        for route in settings.routes:
            provider = provider_of(route)
            if provider is not None:
                providers.setdefault(provider.id, provider)
        return JSONResponse(
            {
                "providers": [
                    {
                        "id": item.id,
                        "displayName": item.display_name,
                        "baseUrl": item.base_url,
                        "keyHint": item.key_hint,
                    }
                    for item in providers.values()
                ],
                "models": model_entries(),
            },
            headers={"x-request-id": request_id, "cache-control": "no-store"},
        )

    def window_of(request: Request) -> tuple[int, int] | JSONResponse:
        now = int(time.time())
        try:
            start = _int_param(request, "start", now - DEFAULT_USAGE_WINDOW_SECONDS)
            end = _int_param(request, "end", now + 1)
        except ValueError:
            return _error(400, "start/end 必须是整数秒", "invalid_request_error", "invalid_window", uuid.uuid4().hex)
        if start >= end:
            return _error(400, "start 必须小于 end", "invalid_request_error", "invalid_window", uuid.uuid4().hex)
        return start, end

    def usage_payload(start: int, end: int, rows: list[dict]) -> dict:
        names = {item.id: item.display_name for item in settings.providers}
        for row in rows:
            row["providerName"] = names.get(row["provider"], row["provider"] or "未记录")
        return {"start": start, "end": end, "models": rows}

    @app.get("/v1/usage/models")
    async def usage_models(request: Request) -> Response:
        """Per provider/key/model totals for the caller; a user only ever sees their own."""
        request_id = uuid.uuid4().hex
        session = authorize(request)
        if session is None:
            return _error(401, "登录已过期，请重新登录", "invalid_request_error", "session_expired", request_id)
        window = window_of(request)
        if isinstance(window, JSONResponse):
            return window
        start, end = window
        rows = session_store.aggregate_models(
            start=start,
            end=end,
            enterprise=session.enterprise,
            username=session.username,
        )
        return JSONResponse(usage_payload(start, end, rows), headers={"x-request-id": request_id, "cache-control": "no-store"})

    if settings.admin_token != "":

        def admin_authorized(request: Request) -> bool:
            token = _bearer_token(request)
            if token is None:
                return False
            return hmac.compare_digest(token.encode("utf-8"), settings.admin_token.encode("utf-8"))

        @app.get("/v1/admin/usage/models")
        async def admin_usage_models(request: Request) -> Response:
            """Same aggregation across every user; requires ZR_GATEWAY_ADMIN_TOKEN."""
            request_id = uuid.uuid4().hex
            if not admin_authorized(request):
                return _error(401, "管理员令牌无效", "authentication_error", "admin_unauthorized", request_id)
            window = window_of(request)
            if isinstance(window, JSONResponse):
                return window
            start, end = window
            rows = session_store.aggregate_models(
                start=start,
                end=end,
                enterprise=request.query_params.get("enterprise", "").strip(),
                username=request.query_params.get("username", "").strip(),
            )
            return JSONResponse(usage_payload(start, end, rows), headers={"x-request-id": request_id, "cache-control": "no-store"})

    return app
