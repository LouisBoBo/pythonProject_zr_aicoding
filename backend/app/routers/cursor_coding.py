"""Cursor 写码过程记录：代理本机 dsh-cursor-coding，并把对话落盘到本工程 docs。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/cursor-coding", tags=["Cursor 写码过程"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs" / "cursor-coding-runs"
PROBE_NAME = "_dsh_cursor_coding_bc_probe.txt"


def _service_base() -> str:
    return os.environ.get("CURSOR_CODING_BASE", "http://127.0.0.1:18788").rstrip("/")


def _ensure_runs_dir() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


class ConfirmBody(BaseModel):
    workspace: str | None = Field(None, description="本机工程绝对路径；默认本仓库根目录")
    requirement: str = Field(..., description="写码诉求")
    write_scope: list[str] = Field(default_factory=list, description="可写相对路径前缀；空表示不限制")
    parent_job_id: str | None = Field(None, description="续改父任务 ID")


class SteerBody(BaseModel):
    message: str = Field(..., description="追问内容")


class ApplyBody(BaseModel):
    accept: list[str] = Field(default_factory=list, description="勾选同步的相对路径")
    reject: list[str] = Field(default_factory=list, description="明确拒绝的路径")
    expand_scope: list[str] = Field(default_factory=list, description="扩大写范围")


async def _upstream_json(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    url = f"{_service_base()}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.request(method, url, json=json_body)
            try:
                data = res.json()
            except Exception:
                data = {"ok": False, "detail": res.text[:500]}
            if not isinstance(data, dict):
                data = {"ok": False, "detail": "上游返回非 JSON 对象", "raw": data}
            return res.status_code, data
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "无法连接 Cursor 写码本机服务 "
                f"{_service_base()}。请先在 dsh-cursor-coding 目录执行：pnpm ui"
            ),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"上游请求失败：{exc}") from exc


def _sanitize_text(value: Any) -> Any:
    if isinstance(value, str):
        # 去掉非法控制字符，保留 \n \r \t
        return "".join(ch for ch in value if ch >= " " or ch in "\n\r\t")
    if isinstance(value, list):
        return [_sanitize_text(x) for x in value]
    if isinstance(value, dict):
        return {k: _sanitize_text(v) for k, v in value.items()}
    return value


def _save_run_snapshot(job_id: str, payload: dict[str, Any]) -> str | None:
    if not job_id:
        return None
    payload = _sanitize_text(payload)
    _ensure_runs_dir()
    md = str(payload.get("markdown") or "")
    json_path = RUNS_DIR / f"{job_id}.json"
    md_path = RUNS_DIR / f"{job_id}.md"
    snap = {
        "job_id": job_id,
        "status": payload.get("status"),
        "detail": payload.get("detail"),
        "workspace": payload.get("workspace"),
        "assistant_text": payload.get("assistant_text") or "",
        "thinking_text": payload.get("thinking_text") or "",
        "transcript": payload.get("transcript") or [],
        "review_in_scope": payload.get("review_in_scope") or [],
        "review_deleted": payload.get("review_deleted") or [],
        "review_deferred": payload.get("review_deferred") or [],
        "synced_files": payload.get("synced_files") or [],
        "saved_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    json_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if md.strip():
        md_path.write_text(md if md.endswith("\n") else md + "\n", encoding="utf-8")
    else:
        # 无 markdown 时本地拼一份
        lines = [
            f"# Cursor 对话回放 · {job_id}",
            "",
            f"- status: {snap['status']}",
            f"- workspace: {snap['workspace']}",
            "",
            "---",
            "",
            "## Thinking",
            "",
            snap["thinking_text"] or "（空）",
            "",
            "## Assistant",
            "",
            snap["assistant_text"] or "（空）",
            "",
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
    return str(md_path)


@router.get(
    "/meta",
    summary="过程查看台元信息",
    description="返回本仓库路径、探针文件、上游 Cursor 写码服务地址与健康状态；页面初始化用。",
)
async def meta(_: User = Depends(get_current_user)) -> dict[str, Any]:
    probe = PROJECT_ROOT / PROBE_NAME
    upstream_ok = False
    upstream_detail = ""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{_service_base()}/health")
            upstream_ok = res.status_code == 200 and bool((res.json() or {}).get("ok"))
            upstream_detail = str((res.json() or {}).get("detail") or "")
    except Exception as exc:  # noqa: BLE001
        upstream_detail = str(exc)
    return {
        "ok": True,
        "project_root": str(PROJECT_ROOT),
        "probe_file": PROBE_NAME,
        "probe_exists": probe.exists(),
        "runs_dir": str(RUNS_DIR),
        "upstream": _service_base(),
        "upstream_ok": upstream_ok,
        "upstream_detail": upstream_detail,
        "default_requirement": (
            f"只修改仓库根目录文件 {PROBE_NAME}：把 color=blue 改成 color=red，"
            "不要改其他文件，不要新建文件。改完写简短说明。"
        ),
    }


@router.post(
    "/prepare-probe",
    summary="准备探针文件",
    description="在本仓库根目录写入/重置 `_dsh_cursor_coding_bc_probe.txt`（color=blue），便于安全演示改码过程。",
)
def prepare_probe(_: User = Depends(get_current_user)) -> dict[str, Any]:
    path = PROJECT_ROOT / PROBE_NAME
    path.write_text("color=blue\nmarker=bc-verify\n", encoding="utf-8")
    return {"ok": True, "path": str(path), "content": path.read_text(encoding="utf-8")}


@router.get(
    "/runs",
    summary="本工程已落盘的过程记录列表",
    description="读取 docs/cursor-coding-runs/ 下历史对话快照，按修改时间倒序。",
)
def list_local_runs(
    limit: int = Query(30, ge=1, le=100, description="最多返回条数"),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    _ensure_runs_dir()
    files = sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    items: list[dict[str, Any]] = []
    for fp in files[:limit]:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            data = {"job_id": fp.stem}
        items.append(
            {
                "job_id": data.get("job_id") or fp.stem,
                "status": data.get("status"),
                "detail": data.get("detail"),
                "assistant_chars": len(str(data.get("assistant_text") or "")),
                "thinking_chars": len(str(data.get("thinking_text") or "")),
                "transcript_count": len(data.get("transcript") or []),
                "saved_at": data.get("saved_at"),
                "json_path": str(fp),
                "md_path": str(fp.with_suffix(".md")),
            }
        )
    return {"ok": True, "count": len(items), "items": items, "runs_dir": str(RUNS_DIR)}


@router.get(
    "/runs/{job_id}",
    summary="读取本工程落盘的单条过程记录",
    description="返回 docs/cursor-coding-runs/{job_id}.json 内容及 markdown 文本。",
)
def get_local_run(job_id: str, _: User = Depends(get_current_user)) -> dict[str, Any]:
    json_path = RUNS_DIR / f"{job_id}.json"
    md_path = RUNS_DIR / f"{job_id}.md"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="本工程未找到该过程记录")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return {"ok": True, **data, "markdown": markdown, "json_path": str(json_path), "md_path": str(md_path)}


@router.post(
    "/confirm",
    summary="确认开工（代理 Cursor 写码）",
    description=(
        "签发 HITL 后调用本机 dsh-cursor-coding 开工；默认 workspace 为本仓库根目录。"
        "返回 job_id，前端用 /jobs/{id}/stream 或轮询 /jobs/{id}/dialog 看完整过程。"
    ),
)
async def confirm(body: ConfirmBody, _: User = Depends(get_current_user)) -> dict[str, Any]:
    workspace = (body.workspace or str(PROJECT_ROOT)).strip()
    requirement = body.requirement.strip()
    if not requirement:
        raise HTTPException(status_code=400, detail="写码诉求不能为空")

    if body.write_scope:
        status, cfg_data = await _upstream_json(
            "PUT",
            "/api/config",
            json_body={"writeScope": body.write_scope},
        )
        if status >= 400:
            raise HTTPException(status_code=status, detail=cfg_data.get("detail") or cfg_data)

    status, issued = await _upstream_json(
        "POST",
        "/api/hitl/issue",
        json_body={
            "action": "cursor-coding.confirm",
            "workspace": workspace,
            "requirement": requirement,
        },
    )
    if status >= 400 or not issued.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=issued.get("detail") or issued)

    payload: dict[str, Any] = {
        "workspace": workspace,
        "requirement": requirement,
        "nonce": issued["nonce"],
    }
    if body.parent_job_id:
        payload["parent_job_id"] = body.parent_job_id

    status, data = await _upstream_json("POST", "/api/cursor-coding/confirm", json_body=payload, timeout=60.0)
    if status >= 400 or not data.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=data.get("detail") or data)
    return {
        "ok": True,
        "job_id": data.get("job_id"),
        "detail": data.get("detail"),
        "stream": f"/api/cursor-coding/jobs/{data.get('job_id')}/stream",
        "dialog": f"/api/cursor-coding/jobs/{data.get('job_id')}/dialog",
        "workspace": workspace,
    }


@router.get(
    "/jobs",
    summary="上游任务列表",
    description="列出本机 Cursor 写码服务中的任务（最近若干条）。",
)
async def list_jobs(_: User = Depends(get_current_user)) -> dict[str, Any]:
    status, data = await _upstream_json("GET", "/api/cursor-coding/jobs")
    if status >= 400:
        raise HTTPException(status_code=status, detail=data.get("detail") or data)
    return data


@router.get(
    "/jobs/{job_id}/dialog",
    summary="完整对话过程（Thinking/工具/正文）",
    description="从上游拉取完整 transcript，并同步落盘到本工程 docs/cursor-coding-runs/。",
)
async def job_dialog(job_id: str, _: User = Depends(get_current_user)) -> dict[str, Any]:
    status, data = await _upstream_json("GET", f"/api/cursor-coding/jobs/{job_id}/dialog")
    if status >= 400:
        raise HTTPException(status_code=status, detail=data.get("detail") or data)
    data = _sanitize_text(data)
    saved = _save_run_snapshot(job_id, data)
    data["saved_md_path"] = saved
    data["saved_json_path"] = str(RUNS_DIR / f"{job_id}.json")
    return data


@router.get(
    "/jobs/{job_id}/stream",
    summary="SSE 过程流（代理）",
    description="透传上游 EventSource 流；前端可用 fetch+ReadableStream 带 JWT 消费。",
)
async def job_stream(job_id: str, _: User = Depends(get_current_user)) -> StreamingResponse:
    url = f"{_service_base()}/api/cursor-coding/jobs/{job_id}/stream"

    async def event_gen():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as res:
                    if res.status_code >= 400:
                        detail = (await res.aread()).decode("utf-8", errors="replace")[:300]
                        yield f"data: {json.dumps({'type': 'error', 'message': detail}, ensure_ascii=False)}\n\n"
                        return
                    async for line in res.aiter_lines():
                        yield line + "\n"
        except httpx.ConnectError:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "error",
                        "message": f"无法连接 {_service_base()}，请先 pnpm ui",
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post(
    "/jobs/{job_id}/steer",
    summary="卡内追问",
    description="在 pending_review 状态下对同一沙箱追问续跑。",
)
async def steer(job_id: str, body: SteerBody, _: User = Depends(get_current_user)) -> dict[str, Any]:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="追问内容不能为空")
    status, issued = await _upstream_json(
        "POST",
        "/api/hitl/issue",
        json_body={"action": "cursor-coding.steer", "job_id": job_id},
    )
    if status >= 400 or not issued.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=issued.get("detail") or issued)
    status, data = await _upstream_json(
        "POST",
        f"/api/cursor-coding/jobs/{job_id}/steer",
        json_body={"nonce": issued["nonce"], "message": message},
        timeout=60.0,
    )
    if status >= 400 or not data.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=data.get("detail") or data)
    return data


@router.post(
    "/jobs/{job_id}/apply",
    summary="审后同步到本机工程",
    description="勾选文件后 HITL 同步；仅同步 accept 列表中的路径。",
)
async def apply(job_id: str, body: ApplyBody, _: User = Depends(get_current_user)) -> dict[str, Any]:
    status, issued = await _upstream_json(
        "POST",
        "/api/hitl/issue",
        json_body={"action": "cursor-coding.apply", "job_id": job_id},
    )
    if status >= 400 or not issued.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=issued.get("detail") or issued)
    status, data = await _upstream_json(
        "POST",
        f"/api/cursor-coding/jobs/{job_id}/apply",
        json_body={
            "nonce": issued["nonce"],
            "accept": body.accept,
            "reject": body.reject,
            "expand_scope": body.expand_scope,
        },
        timeout=60.0,
    )
    if status >= 400 or not data.get("ok"):
        raise HTTPException(status_code=status if status >= 400 else 400, detail=data.get("detail") or data)
    # 同步后再拉一次 dialog 落盘
    try:
        _, dialog = await _upstream_json("GET", f"/api/cursor-coding/jobs/{job_id}/dialog")
        if dialog.get("ok"):
            _save_run_snapshot(job_id, dialog)
    except Exception:
        pass
    return data
