"""员工工时报表：按工单报工明细查询。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Employee, User, WorkOrderLaborRecord

router = APIRouter(prefix="/api/reports", tags=["报表中心"])


class EmployeeWorkHoursFilterEmployee(BaseModel):
    employee_no: str
    employee_name: str
    department_name: str


class EmployeeWorkHoursFiltersResponse(BaseModel):
    departments: list[str] = Field(description="部门/班组列表")
    employees: list[EmployeeWorkHoursFilterEmployee] = Field(description="员工下拉选项")


class EmployeeWorkHoursReportItem(BaseModel):
    id: int
    employee_no: str
    employee_name: str
    department_name: str
    work_date: date
    order_no: str
    process: str
    work_hours: float = Field(description="工时（小时）")


class EmployeeWorkHoursReportListResponse(BaseModel):
    items: list[EmployeeWorkHoursReportItem]
    total: int
    page: int
    page_size: int
    work_hours_sum: float = Field(description="当前筛选条件下工时合计")


def _apply_employee_work_hours_filters(
    query,
    *,
    date_from: date,
    date_to: date,
    employee_no: str | None,
    department_name: str | None,
):
    query = query.filter(
        WorkOrderLaborRecord.work_date >= date_from,
        WorkOrderLaborRecord.work_date <= date_to,
    )
    if employee_no:
        query = query.filter(WorkOrderLaborRecord.employee_no == employee_no)
    if department_name:
        query = query.filter(WorkOrderLaborRecord.department_name == department_name)
    return query


def _to_report_item(row: WorkOrderLaborRecord) -> EmployeeWorkHoursReportItem:
    order_no = row.work_order.order_no if row.work_order else "—"
    return EmployeeWorkHoursReportItem(
        id=row.id,
        employee_no=row.employee_no,
        employee_name=row.employee_name,
        department_name=row.department_name,
        work_date=row.work_date,
        order_no=order_no,
        process=row.process or "—",
        work_hours=round(float(row.work_hours or 0), 2),
    )


@router.get(
    "/employee-work-hours/filters",
    response_model=EmployeeWorkHoursFiltersResponse,
    summary="员工工时报表筛选选项",
    description="返回部门/班组与员工列表，供工时报表筛选下拉使用。",
)
def list_employee_work_hours_filters(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    departments = sorted(
        {
            name
            for (name,) in db.query(WorkOrderLaborRecord.department_name)
            .distinct()
            .all()
            if name
        }
    )
    if not departments:
        departments = sorted(
            {
                emp.department_name
                for emp in db.query(Employee).filter(Employee.status == "在职").all()
                if emp.department_name
            }
        )

    labor_employees = (
        db.query(
            WorkOrderLaborRecord.employee_no,
            WorkOrderLaborRecord.employee_name,
            WorkOrderLaborRecord.department_name,
        )
        .distinct()
        .order_by(WorkOrderLaborRecord.employee_no)
        .all()
    )
    employees = [
        EmployeeWorkHoursFilterEmployee(
            employee_no=no,
            employee_name=name,
            department_name=dept,
        )
        for no, name, dept in labor_employees
    ]
    if not employees:
        employees = [
            EmployeeWorkHoursFilterEmployee(
                employee_no=emp.employee_no,
                employee_name=emp.employee_name,
                department_name=emp.department_name,
            )
            for emp in db.query(Employee)
            .filter(Employee.status == "在职")
            .order_by(Employee.employee_no)
            .all()
        ]

    return EmployeeWorkHoursFiltersResponse(departments=departments, employees=employees)


@router.get(
    "/employee-work-hours",
    response_model=EmployeeWorkHoursReportListResponse,
    summary="员工工时报表",
    description=(
        "按工单报工明细列出员工工时：员工、部门/班组、日期、工单号、工序与工时；"
        "支持按员工、部门、日期区间筛选与分页；默认近 7 日（含今天）。"
    ),
)
def list_employee_work_hours_report(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    date_from: date | None = Query(None, description="报工日期起（含）"),
    date_to: date | None = Query(None, description="报工日期止（含）"),
    employee_no: str | None = Query(None, description="员工工号（精确匹配）"),
    department_name: str | None = Query(None, description="部门/班组（精确匹配）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=6)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    base_query = db.query(WorkOrderLaborRecord).options(
        joinedload(WorkOrderLaborRecord.work_order)
    )
    base_query = _apply_employee_work_hours_filters(
        base_query,
        date_from=date_from,
        date_to=date_to,
        employee_no=employee_no,
        department_name=department_name,
    )

    sum_query = _apply_employee_work_hours_filters(
        db.query(func.coalesce(func.sum(WorkOrderLaborRecord.work_hours), 0)),
        date_from=date_from,
        date_to=date_to,
        employee_no=employee_no,
        department_name=department_name,
    )
    work_hours_sum = round(float(sum_query.scalar() or 0), 2)

    total = base_query.count()
    rows = (
        base_query.order_by(
            WorkOrderLaborRecord.work_date.desc(),
            WorkOrderLaborRecord.employee_no,
            WorkOrderLaborRecord.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return EmployeeWorkHoursReportListResponse(
        items=[_to_report_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        work_hours_sum=work_hours_sum,
    )
