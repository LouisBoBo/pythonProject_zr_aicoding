"""用户管理（需 settings.admin）：列表 / 创建 / 重置密码 / 改角色。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import hash_password
from app.database import get_db
from app.models import User
from app.permissions import SETTINGS_ADMIN, require_permissions
from app.schemas import (
    UserCreateRequest,
    UserListItem,
    UserListResponse,
    UserResetPasswordRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])

VALID_ROLES = frozenset({"admin", "manager", "user"})


def _admin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == "admin")
        .count()
    )


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.get("", response_model=UserListResponse, summary="用户列表")
def list_users(
    _current_user: User = Depends(require_permissions(SETTINGS_ADMIN)),
    db: Session = Depends(get_db),
):
    rows = db.query(User).order_by(User.id.asc()).all()
    return UserListResponse(
        items=[UserListItem.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=201,
    summary="创建用户",
)
def create_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_permissions(SETTINGS_ADMIN)),
    db: Session = Depends(get_db),
):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    role = payload.role if payload.role in VALID_ROLES else "user"
    user = User(
        username=username,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        username=current_user.username,
        action="create",
        resource="user",
        resource_id=user.id,
        detail={"username": user.username, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        permissions=[],
    )


@router.post(
    "/{user_id}/reset-password",
    summary="重置用户密码",
)
def reset_user_password(
    user_id: int,
    payload: UserResetPasswordRequest,
    current_user: User = Depends(require_permissions(SETTINGS_ADMIN)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    user.hashed_password = hash_password(payload.new_password)
    record_audit(
        db,
        username=current_user.username,
        action="reset_password",
        resource="user",
        resource_id=user.id,
        detail={"username": user.username},
    )
    db.commit()
    return {"ok": True}


@router.patch(
    "/{user_id}",
    response_model=UserListItem,
    summary="更新用户角色",
    description="至少保留一名 admin；禁止将最后一名 admin 降级。",
)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_permissions(SETTINGS_ADMIN)),
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(user_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        new_role = data["role"]
        if new_role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="角色无效")
        if user.role == "admin" and new_role != "admin" and _admin_count(db) <= 1:
            raise HTTPException(
                status_code=400,
                detail="至少保留一名管理员",
            )
        user.role = new_role
        record_audit(
            db,
            username=current_user.username,
            action="update_role",
            resource="user",
            resource_id=user.id,
            detail={"username": user.username, "role": new_role},
        )
        db.commit()
        db.refresh(user)
    return UserListItem.model_validate(user)
