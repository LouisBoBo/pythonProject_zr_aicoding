"""操作审计写入服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog

# 禁止写入审计的敏感字段
_SENSITIVE_KEYS = frozenset(
    {"password", "hashed_password", "access_token", "token", "secret", "secret_key"}
)


def _sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if not detail:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in detail.items():
        if key.lower() in _SENSITIVE_KEYS:
            continue
        cleaned[key] = value
    return cleaned or None


def record_audit(
    db: Session,
    *,
    username: str,
    action: str,
    resource: str = "",
    resource_id: str | int | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
    success: bool = True,
    commit: bool = False,
) -> AuditLog:
    """追加一条审计记录。默认不单独 commit，由调用方业务事务一并提交。"""
    row = AuditLog(
        username=(username or "")[:50],
        action=action[:50],
        resource=(resource or "")[:50],
        resource_id=None if resource_id is None else str(resource_id)[:80],
        detail=_sanitize_detail(detail),
        ip=(ip or None) and str(ip)[:64],
        success=success,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row
