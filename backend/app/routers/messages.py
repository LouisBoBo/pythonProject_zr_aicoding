"""消息中心 API — 系统通知、业务告警与公告查询。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.message_utils import CATEGORY_BY_MESSAGE_LEVEL
from app.models import Message, User
from app.schemas import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageStatsResponse,
    MessageUnreadCountResponse,
    MessageUpdate,
)

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _get_message_or_404(message_id: int, db: Session) -> Message:
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    return message


@router.get("/unread-count", response_model=MessageUnreadCountResponse)
def unread_count(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """未读消息总数。"""
    count = db.query(Message).filter(Message.is_read.is_(False)).count()
    return MessageUnreadCountResponse(count=count)


@router.get("/stats", response_model=MessageStatsResponse)
def message_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """未读消息数量统计（按分类）。"""
    unread = db.query(Message).filter(Message.is_read.is_(False))
    return MessageStatsResponse(
        total=unread.count(),
        system=unread.filter(Message.category == "system").count(),
        alert=unread.filter(Message.category == "alert").count(),
        announcement=unread.filter(Message.category == "announcement").count(),
    )


@router.get("", response_model=MessageListResponse)
def list_messages(
    page: int = Query(1, ge=1),
    size: int | None = Query(None, ge=1, le=100),
    page_size: int | None = Query(None, ge=1, le=100),
    category: str | None = Query(None, description="system / alert / announcement"),
    level: str | None = Query(None, description="high / medium / low，按消息类型映射的等级筛选"),
    is_read: bool | None = Query(None),
    keyword: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """分页查询消息列表。"""
    effective_size = size if size is not None else (page_size if page_size is not None else 20)

    query = db.query(Message)
    if category:
        query = query.filter(Message.category == category)
    if level:
        level_category = CATEGORY_BY_MESSAGE_LEVEL.get(level)
        if level_category:
            query = query.filter(Message.category == level_category)
    if is_read is not None:
        query = query.filter(Message.is_read.is_(is_read))
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(Message.title.like(like) | Message.content.like(like))

    total = query.count()
    items = (
        query.order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * effective_size)
        .limit(effective_size)
        .all()
    )
    return MessageListResponse(
        items=[MessageResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=effective_size,
    )


@router.post("", response_model=MessageResponse, status_code=201)
def create_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """新建消息。"""
    message = Message(
        title=payload.title.strip(),
        content=payload.content.strip(),
        category=payload.category,
        priority=payload.priority,
        source=payload.source.strip() if payload.source else None,
        link=payload.link.strip() if payload.link else None,
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageResponse.model_validate(message)


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """获取单条消息详情。"""
    return MessageResponse.model_validate(_get_message_or_404(message_id, db))


@router.put("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: int,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """更新消息。"""
    message = _get_message_or_404(message_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(message, field, value)
    db.commit()
    db.refresh(message)
    return MessageResponse.model_validate(message)


@router.delete("/{message_id}", status_code=204)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """删除消息。"""
    message = _get_message_or_404(message_id, db)
    db.delete(message)
    db.commit()


def _mark_message_read(message_id: int, db: Session) -> MessageResponse:
    message = _get_message_or_404(message_id, db)
    message.is_read = True
    db.commit()
    db.refresh(message)
    return MessageResponse.model_validate(message)


@router.post("/{message_id}/read", response_model=MessageResponse)
def mark_message_read_post(
    message_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """标记单条消息为已读（POST）。"""
    return _mark_message_read(message_id, db)


@router.patch("/{message_id}/read", response_model=MessageResponse)
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """标记单条消息为已读（PATCH，兼容旧客户端）。"""
    return _mark_message_read(message_id, db)


@router.patch("/read-all")
def mark_all_read(
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """全部标记为已读，可按分类筛选。"""
    query = db.query(Message).filter(Message.is_read.is_(False))
    if category:
        query = query.filter(Message.category == category)
    updated = query.update({Message.is_read: True}, synchronize_session=False)
    db.commit()
    return {"updated": updated}
