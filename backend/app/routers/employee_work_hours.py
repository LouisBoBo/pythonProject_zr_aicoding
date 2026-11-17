"""员工工时列表（工单报工明细）。"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WorkOrderLaborRecord

router = APIRouter(prefix="/api/employee-work-hours", tags=["员工工时"])


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


def _to_item(row: WorkOrderLaborRecord) -> EmployeeWorkHourListItem:
    order_no = row.work_order.order_no if row.work_order else "—"
    return EmployeeWorkHourListItem(
        id=row.id,
        employee_no=row.employee_no,
        employee_name=row.employee_name,
        department=row.department_name,
        project_name=order_no,
        task_name=row.process or "—",
        work_date=row.work_date,
        shift_type=None,
        work_hours=round(float(row.work_hours or 0), 2),
        overtime_hours=0.0,
        approval_status="已通过",
        created_at=row.created_at,
    )


@router.get(
    "",
    response_model=EmployeeWorkHourListResponse,
    summary="员工工时列表",
    description="分页查询工单报工工时明细；员工工时列表页数据来自本接口。",
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
        None, description="审批状态：pending / approved / rejected（工单报工无审批流，仅兼容入参）"
    ),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del approval_status  # 工单报工明细无审批状态筛选
    query = db.query(WorkOrderLaborRecord).options(joinedload(WorkOrderLaborRecord.work_order))
    if employee_no:
        query = query.filter(WorkOrderLaborRecord.employee_no.ilike(f"%{employee_no.strip()}%"))
    if employee_name:
        query = query.filter(
            WorkOrderLaborRecord.employee_name.ilike(f"%{employee_name.strip()}%")
        )
    if department:
        query = query.filter(
            WorkOrderLaborRecord.department_name.ilike(f"%{department.strip()}%")
        )
    if date_from:
        query = query.filter(WorkOrderLaborRecord.work_date >= date_from)
    if date_to:
        query = query.filter(WorkOrderLaborRecord.work_date <= date_to)

    total = query.count()
    rows = (
        query.order_by(
            WorkOrderLaborRecord.work_date.desc(),
            WorkOrderLaborRecord.employee_no.asc(),
            WorkOrderLaborRecord.id.desc(),
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