"""审计日志查询（需 audit.read）。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.permissions import AUDIT_READ, require_permissions

router = APIRouter(prefix="/api/audit-logs", tags=["审计日志"])


class AuditLogItem(BaseModel):
    id: int
    username: str
    action: str
    resource: str
    resource_id: str | None = None
    detail: dict | None = None
    ip: str | None = None
    success: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="审计日志列表",
    description="分页查询操作审计；需 audit.read 权限（管理员默认具备）。",
)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    username: str | None = Query(None, description="操作人（模糊）"),
    action: str | None = Query(None, description="动作（模糊）"),
    resource: str | None = Query(None, description="资源类型"),
    _current_user: User = Depends(require_permissions(AUDIT_READ)),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username.strip()}%"))
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    if resource:
        query = query.filter(AuditLog.resource == resource.strip())
    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogListResponse(
        items=[AuditLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
