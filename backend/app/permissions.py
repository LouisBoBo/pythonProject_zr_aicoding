"""RBAC：权限码常量、角色映射、依赖守卫。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import SessionLocal, get_db
from app.models import Permission, RolePermission, User

# ---- 权限码 ----
WORK_ORDERS_WRITE = "work_orders.write"
INVENTORY_WRITE = "inventory.write"
SALES_WRITE = "sales.write"
MESSAGES_WRITE = "messages.write"
KANBAN_WRITE = "kanban.write"
EQUIPMENT_WRITE = "equipment.write"
WORK_HOURS_APPROVE = "work_hours.approve"
REPORTS_READ = "reports.read"
SETTINGS_ADMIN = "settings.admin"
AUDIT_READ = "audit.read"
EMPLOYEES_READ = "employees.read"
MATERIALS_READ = "materials.read"

ALL_PERMISSION_CODES: list[tuple[str, str]] = [
    (WORK_ORDERS_WRITE, "工单写操作"),
    (INVENTORY_WRITE, "库存入库/出库写操作"),
    (SALES_WRITE, "销售订单与发货写操作"),
    (MESSAGES_WRITE, "消息中心写操作"),
    (KANBAN_WRITE, "看板配置写操作"),
    (EQUIPMENT_WRITE, "设备台账写操作"),
    (WORK_HOURS_APPROVE, "员工工时审批"),
    (REPORTS_READ, "报表只读"),
    (SETTINGS_ADMIN, "系统设置管理"),
    (AUDIT_READ, "审计日志查询"),
    (EMPLOYEES_READ, "员工列表只读"),
    (MATERIALS_READ, "物料主数据只读"),
]

# admin 硬编码全放行；下列为 manager / user 默认映射
ROLE_DEFAULT_PERMISSIONS: dict[str, list[str]] = {
    "manager": [
        WORK_ORDERS_WRITE,
        INVENTORY_WRITE,
        SALES_WRITE,
        MESSAGES_WRITE,
        KANBAN_WRITE,
        EQUIPMENT_WRITE,
        WORK_HOURS_APPROVE,
        REPORTS_READ,
        EMPLOYEES_READ,
        MATERIALS_READ,
    ],
    "user": [
        REPORTS_READ,
        EMPLOYEES_READ,
        MATERIALS_READ,
    ],
}

ADMIN_ROLE = "admin"


def is_admin(user: User) -> bool:
    return (user.role or "").strip().lower() == ADMIN_ROLE


def user_permission_codes(db: Session, user: User) -> set[str]:
    if is_admin(user):
        return {code for code, _ in ALL_PERMISSION_CODES}
    role = (user.role or "").strip() or "user"
    rows = (
        db.query(RolePermission.permission_code)
        .filter(RolePermission.role == role)
        .all()
    )
    return {row[0] for row in rows}


def user_has_permissions(db: Session, user: User, *codes: str) -> bool:
    if not codes:
        return True
    if is_admin(user):
        return True
    owned = user_permission_codes(db, user)
    return all(code in owned for code in codes)


def require_permissions(*codes: str) -> Callable:
    """FastAPI 依赖：要求当前用户具备全部给定权限码。"""

    def _dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not user_has_permissions(db, current_user, *codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限",
            )
        return current_user

    return _dependency


def seed_rbac() -> None:
    """幂等写入权限码、角色映射，以及演示只读账号 viewer。"""
    from app.auth import hash_password

    db = SessionLocal()
    try:
        existing_codes = {p.code for p in db.query(Permission).all()}
        for code, name in ALL_PERMISSION_CODES:
            if code not in existing_codes:
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

        if not db.query(User).filter(User.username == "viewer").first():
            db.add(
                User(
                    username="viewer",
                    hashed_password=hash_password("viewer123"),
                    role="user",
                )
            )
        db.commit()
    finally:
        db.close()
