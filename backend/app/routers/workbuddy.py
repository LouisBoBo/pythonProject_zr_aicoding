"""AI 工作助手：代理本机 ZR-WorkBuddy。

用户访问地址通常为 Web 界面 http://127.0.0.1:3081 ；聊天 API 在本机引擎端口（默认自动探测 8000 / 18000）。
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/workbuddy", tags=["AI工作助手"])

_DEFAULT_WEB = "http://127.0.0.1:3081"
_DEFAULT_API_CANDIDATES = ("http://127.0.0.1:8000", "http://127.0.0.1:18000")
_resolved_api_base: str | None = None


def _web_url() -> str:
    return os.environ.get("WORKBUDDY_WEB_URL", _DEFAULT_WEB).rstrip("/")


def _api_candidates() -> list[str]:
    explicit = os.environ.get("WORKBUDDY_API_BASE", "").strip()
    if explicit:
        return [explicit.rstrip("/")]
    legacy = os.environ.get("WORKBUDDY_BASE", "").strip()
    if legacy:
        base = legacy.rstrip("/")
        if base != _web_url():
            return [base]
    return list(_DEFAULT_API_CANDIDATES)


async def _probe_api_base(client: httpx.AsyncClient, base: str) -> bool:
    try:
        res = await client.get(f"{base}/openapi.json")
        if res.status_code != 200:
            return False
        data = res.json()
        return "/api/chat/stream" in (data.get("paths") or {})
    except Exception:
        return False


async def _resolve_api_base(client: httpx.AsyncClient | None = None) -> str | None:
    global _resolved_api_base
    if _resolved_api_base:
        return _resolved_api_base

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=3.0)

    try:
        for base in _api_candidates():
            if await _probe_api_base(client, base):
                _resolved_api_base = base
                return base
        return None
    finally:
        if owns_client and client is not None:
            await client.aclose()


async def _check_api_health(client: httpx.AsyncClient, base: str) -> tuple[bool, str]:
    """判定本机 API 引擎是否可转发聊天（不依赖 /api/status，避免 demo 首请求 >3s 误判）。"""
    try:
        res = await client.get(f"{base}/api/workbuddy/health", timeout=8.0)
        if res.status_code == 200:
            data = res.json() if res.content else {}
            # ready = tools + LLM；对话代理只需引擎，不要求用户一定开着 3081 页面
            ok = bool(data.get("ready"))
            hint = ""
            dsh = (data or {}).get("dsh_web") or {}
            if isinstance(dsh, dict):
                hint = str(dsh.get("hint") or "")
            detail = hint or f"health ready={data.get('ready')}"
            return ok, detail[:200]
    except Exception:
        pass

    try:
        res = await client.get(f"{base}/api/runtime", timeout=5.0)
        if res.status_code == 200:
            data = res.json() if res.content else {}
            ok = bool(data.get("ok")) and bool(data.get("tools_ready"))
            return ok, "runtime"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    try:
        res = await client.get(f"{base}/api/status", timeout=20.0)
        if res.status_code == 200:
            data = res.json() if res.content else {}
            return bool((data or {}).get("ok", True)), "status"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    try:
        res = await client.get(f"{base}/openapi.json", timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            if "/api/chat/stream" in (data.get("paths") or {}):
                return True, "openapi"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return False, "health/runtime 均不可用"


class ChatBody(BaseModel):
    message: str = Field(..., description="用户问题")
    code_dev_brief: dict[str, Any] | None = Field(None, description="写码上下文（可选）")


@router.get(
    "/meta",
    summary="WorkBuddy 连接状态",
    description="返回 WorkBuddy Web 访问地址、本机 API 引擎地址与健康状态。",
)
async def meta(_: User = Depends(get_current_user)) -> dict[str, Any]:
    upstream_ok = False
    upstream_detail = ""
    upstream = ""
    async with httpx.AsyncClient(timeout=10.0) as client:
        api_base = await _resolve_api_base(client)
        if api_base:
            upstream = api_base
            upstream_ok, upstream_detail = await _check_api_health(client, api_base)
        else:
            upstream_detail = "未找到可用的 WorkBuddy API 引擎（可设置 WORKBUDDY_API_BASE=http://127.0.0.1:8000）"

    return {
        "ok": True,
        "web_url": _web_url(),
        "upstream": upstream,
        "upstream_ok": upstream_ok,
        "upstream_detail": upstream_detail,
    }


@router.post(
    "/chat/stream",
    summary="流式对话（代理 WorkBuddy）",
    description=(
        "SSE 透传上游 /api/chat/stream：status / thinking / reply（增量）/ done / error。"
        "前端用 fetch + ReadableStream 并携带 ERP JWT。"
    ),
)
async def chat_stream(body: ChatBody, _: User = Depends(get_current_user)) -> StreamingResponse:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="问题不能为空")

    payload: dict[str, Any] = {"message": message}
    if body.code_dev_brief is not None:
        payload["code_dev_brief"] = body.code_dev_brief

    async def event_gen():
        async with httpx.AsyncClient(timeout=None) as client:
            api_base = await _resolve_api_base(client)
            if not api_base:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "error",
                            "message": (
                                f"未找到 WorkBuddy API 引擎。请先打开 {_web_url()} ，"
                                "或设置环境变量 WORKBUDDY_API_BASE。"
                            ),
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
                return

            url = f"{api_base}/api/chat/stream"
            try:
                async with client.stream("POST", url, json=payload) as res:
                    if res.status_code >= 400:
                        detail = (await res.aread()).decode("utf-8", errors="replace")[:500]
                        yield (
                            "data: "
                            + json.dumps({"type": "error", "message": detail}, ensure_ascii=False)
                            + "\n\n"
                        )
                        return
                    async for line in res.aiter_lines():
                        if line is None:
                            continue
                        yield line + "\n"
            except httpx.ConnectError:
                global _resolved_api_base
                _resolved_api_base = None
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "error",
                            "message": (
                                f"无法连接 WorkBuddy API（{api_base}）。"
                                f"请确认已在浏览器打开 {_web_url()} 且桌面端已启动。"
                            ),
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
            except httpx.HTTPError as exc:
                yield (
                    "data: "
                    + json.dumps({"type": "error", "message": f"上游请求失败：{exc}"}, ensure_ascii=False)
                    + "\n\n"
                )

    return StreamingResponse(event_gen(), media_type="text/event-stream")
