"""员工工时列表（明细填报记录）。"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import EmployeeWorkHour, User

router = APIRouter(prefix="/api/employee-work-hours", tags=["员工工时"])

APPROVAL_LABELS = {
    "pending": "待审批",
    "approved": "已通过",
    "rejected": "已驳回",
}


class EmployeeWorkHourListItem(BaseModel):
    """员工工时列表行。"""

    id: int = Field(description="记录 ID")
    employee_no: str = Field(description="工号")
    employee_name: str = Field(description="姓名")
    department: str = Field(description="部门")
    project_name: str = Field(description="项目")
    task_name: str = Field(description="任务")
    work_date: date = Field(description="报工日期")
    shift_type: str | None = Field(default=None, description="班别")
    work_hours: float = Field(description="工时（小时）")
    overtime_hours: float = Field(description="加班工时（小时）")
    approval_status: str = Field(description="审批状态")
    created_at: datetime = Field(description="创建时间")


class EmployeeWorkHourListResponse(BaseModel):
    items: list[EmployeeWorkHourListItem]
    total: int
    page: int
    page_size: int


def _approval_label(status: str | None) -> str:
    if not status:
        return "—"
    return APPROVAL_LABELS.get(status, status)


def _to_item(row: EmployeeWorkHour) -> EmployeeWorkHourListItem:
    return EmployeeWorkHourListItem(
        id=row.id,
        employee_no=row.employee_no,
        employee_name=row.employee_name,
        department=row.department,
        project_name=row.project_name,
        task_name=row.task_name,
        work_date=row.work_date,
        shift_type=row.shift_type,
        work_hours=round(float(row.work_hours or 0), 2),
        overtime_hours=round(float(row.overtime_hours or 0), 2),
        approval_status=_approval_label(row.approval_status),
        created_at=row.created_at,
    )


@router.get(
    "",
    response_model=EmployeeWorkHourListResponse,
    summary="员工工时列表",
    description="分页查询员工工时填报明细；员工工时列表页数据来自本接口。",
)
def list_employee_work_hours(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    employee_no: str | None = Query(None, description="工号（模糊匹配）"),
    employee_name: str | None = Query(None, description="姓名（模糊匹配）"),
    department: str | None = Query(None, description="部门（模糊匹配）"),
    date_from: date | None = Query(None, description="报工日期起（含）"),
    date_to: date | None = Query(None, description="报工日期止（含）"),
    approval_status: str | None = Query(
        None, description="审批状态：pending / approved / rejected"
    ),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(EmployeeWorkHour)
    if employee_no:
        query = query.filter(EmployeeWorkHour.employee_no.ilike(f"%{employee_no.strip()}%"))
    if employee_name:
        query = query.filter(
            EmployeeWorkHour.employee_name.ilike(f"%{employee_name.strip()}%")
        )
    if department:
        query = query.filter(EmployeeWorkHour.department.ilike(f"%{department.strip()}%"))
    if date_from:
        query = query.filter(EmployeeWorkHour.work_date >= date_from)
    if date_to:
        query = query.filter(EmployeeWorkHour.work_date <= date_to)
    if approval_status:
        query = query.filter(EmployeeWorkHour.approval_status == approval_status.strip())

    total = query.count()
    rows = (
        query.order_by(
            EmployeeWorkHour.work_date.desc(),
            EmployeeWorkHour.employee_no.asc(),
            EmployeeWorkHour.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return EmployeeWorkHourListResponse(
        items=[_to_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
