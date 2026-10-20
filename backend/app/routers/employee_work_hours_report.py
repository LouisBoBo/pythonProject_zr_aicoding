"""员工工时报表 API（报表中心）。"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import EmployeeWorkHour, User
from app.schemas import (
    EmployeeWorkHourFilterEmployee,
    EmployeeWorkHourFiltersResponse,
    EmployeeWorkHourReportItem,
    EmployeeWorkHourReportListResponse,
)

router = APIRouter(prefix="/api/reports", tags=["报表中心"])

WORK_HOUR_DIMENSIONS = (
    "detail",
    "employee",
    "employee_date",
    "employee_month",
    "project",
    "department",
)

WORK_HOUR_APPROVAL_LABELS = {
    "pending": "待审批",
    "approved": "已通过",
    "rejected": "已驳回",
}

WORK_HOUR_SHIFT_LABELS = {
    "day": "白班",
    "night": "晚班",
}


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def _work_hour_approval_label(status: str | None) -> str:
    if not status:
        return "—"
    return WORK_HOUR_APPROVAL_LABELS.get(status, status)


def _work_hour_shift_label(shift: str | None) -> str | None:
    if not shift:
        return None
    if shift in WORK_HOUR_SHIFT_LABELS.values():
        return shift
    return WORK_HOUR_SHIFT_LABELS.get(shift, shift)


def _normalize_shift_type_filter(shift_type: str | None) -> str | None:
    if not shift_type:
        return None
    if shift_type in WORK_HOUR_SHIFT_LABELS:
        return shift_type
    for code, label in WORK_HOUR_SHIFT_LABELS.items():
        if shift_type == label:
            return code
    return shift_type


def _normalize_work_hour_dimension(dimension: str) -> str:
    if dimension not in WORK_HOUR_DIMENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 dimension，可选：{', '.join(WORK_HOUR_DIMENSIONS)}",
        )
    return dimension


def _apply_work_hour_report_filters(
    query,
    *,
    date_from: date,
    date_to: date,
    department: str | None,
    employee_no: str | None,
    project_name: str | None,
    approval_status: str | None,
    shift_type: str | None,
):
    query = query.filter(
        EmployeeWorkHour.work_date >= date_from,
        EmployeeWorkHour.work_date <= date_to,
    )
    if department:
        query = query.filter(EmployeeWorkHour.department == department)
    if employee_no:
        query = query.filter(EmployeeWorkHour.employee_no == employee_no)
    if project_name:
        query = query.filter(EmployeeWorkHour.project_name == project_name)
    if approval_status:
        query = query.filter(EmployeeWorkHour.approval_status == approval_status)
    if shift_type:
        query = query.filter(EmployeeWorkHour.shift_type == shift_type)
    return query


def _build_work_hour_report_items(
    query,
    dimension: str,
) -> list[EmployeeWorkHourReportItem]:
    if dimension == "detail":
        rows = (
            query.order_by(
                EmployeeWorkHour.work_date.desc(),
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.id.desc(),
            ).all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name=row.employee_name,
                employee_no=row.employee_no,
                department=row.department,
                work_date=_as_date(row.work_date),
                shift_type=_work_hour_shift_label(row.shift_type),
                project_name=row.project_name,
                task_name=row.task_name,
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status=_work_hour_approval_label(row.approval_status),
            )
            for row in rows
        ]

    if dimension == "employee":
        rows = (
            query.with_entities(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
                func.sum(EmployeeWorkHour.work_hours).label("work_hours"),
                func.sum(EmployeeWorkHour.overtime_hours).label("overtime_hours"),
                func.count(EmployeeWorkHour.id).label("record_count"),
            )
            .group_by(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
            )
            .order_by(EmployeeWorkHour.employee_no)
            .all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name=row.employee_name,
                employee_no=row.employee_no,
                department=row.department,
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status="汇总",
                record_count=int(row.record_count or 0),
            )
            for row in rows
        ]

    if dimension == "employee_date":
        rows = (
            query.with_entities(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
                EmployeeWorkHour.work_date,
                func.sum(EmployeeWorkHour.work_hours).label("work_hours"),
                func.sum(EmployeeWorkHour.overtime_hours).label("overtime_hours"),
                func.count(EmployeeWorkHour.id).label("record_count"),
            )
            .group_by(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
                EmployeeWorkHour.work_date,
            )
            .order_by(
                EmployeeWorkHour.work_date.desc(),
                EmployeeWorkHour.employee_no,
            )
            .all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name=row.employee_name,
                employee_no=row.employee_no,
                department=row.department,
                work_date=_as_date(row.work_date),
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status="汇总",
                record_count=int(row.record_count or 0),
            )
            for row in rows
        ]

    if dimension == "employee_month":
        month_expr = func.strftime("%Y-%m", EmployeeWorkHour.work_date)
        rows = (
            query.with_entities(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
                month_expr.label("work_month"),
                func.sum(EmployeeWorkHour.work_hours).label("work_hours"),
                func.sum(EmployeeWorkHour.overtime_hours).label("overtime_hours"),
                func.count(EmployeeWorkHour.id).label("record_count"),
            )
            .group_by(
                EmployeeWorkHour.employee_no,
                EmployeeWorkHour.employee_name,
                EmployeeWorkHour.department,
                month_expr,
            )
            .order_by(month_expr.desc(), EmployeeWorkHour.employee_no)
            .all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name=row.employee_name,
                employee_no=row.employee_no,
                department=row.department,
                work_month=row.work_month,
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status="汇总",
                record_count=int(row.record_count or 0),
            )
            for row in rows
        ]

    if dimension == "project":
        rows = (
            query.with_entities(
                EmployeeWorkHour.project_name,
                EmployeeWorkHour.department,
                func.sum(EmployeeWorkHour.work_hours).label("work_hours"),
                func.sum(EmployeeWorkHour.overtime_hours).label("overtime_hours"),
                func.count(EmployeeWorkHour.id).label("record_count"),
            )
            .group_by(EmployeeWorkHour.project_name, EmployeeWorkHour.department)
            .order_by(EmployeeWorkHour.project_name)
            .all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name="—",
                employee_no="—",
                department=row.department,
                project_name=row.project_name,
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status="汇总",
                record_count=int(row.record_count or 0),
            )
            for row in rows
        ]

    if dimension == "department":
        rows = (
            query.with_entities(
                EmployeeWorkHour.department,
                func.sum(EmployeeWorkHour.work_hours).label("work_hours"),
                func.sum(EmployeeWorkHour.overtime_hours).label("overtime_hours"),
                func.count(EmployeeWorkHour.id).label("record_count"),
            )
            .group_by(EmployeeWorkHour.department)
            .order_by(EmployeeWorkHour.department)
            .all()
        )
        return [
            EmployeeWorkHourReportItem(
                employee_name="—",
                employee_no="—",
                department=row.department,
                work_hours=round(float(row.work_hours or 0), 2),
                overtime_hours=round(float(row.overtime_hours or 0), 2),
                approval_status="汇总",
                record_count=int(row.record_count or 0),
            )
            for row in rows
        ]

    raise HTTPException(status_code=400, detail="不支持的统计维度")


@router.get(
    "/employee-work-hours/filters",
    response_model=EmployeeWorkHourFiltersResponse,
    summary="员工工时报表筛选选项",
    description="返回部门、员工、项目下拉选项，供员工工时报表筛选使用。",
)
def list_employee_work_hour_filters(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    departments = sorted(
        {
            dept
            for (dept,) in db.query(EmployeeWorkHour.department)
            .distinct()
            .order_by(EmployeeWorkHour.department)
            .all()
            if dept
        }
    )
    employee_rows = (
        db.query(EmployeeWorkHour.employee_no, EmployeeWorkHour.employee_name)
        .distinct()
        .order_by(EmployeeWorkHour.employee_no)
        .all()
    )
    employees = [
        EmployeeWorkHourFilterEmployee(
            employee_no=row.employee_no,
            employee_name=row.employee_name,
        )
        for row in employee_rows
    ]
    projects = sorted(
        {
            name
            for (name,) in db.query(EmployeeWorkHour.project_name)
            .distinct()
            .order_by(EmployeeWorkHour.project_name)
            .all()
            if name
        }
    )
    return EmployeeWorkHourFiltersResponse(
        departments=departments,
        employees=employees,
        projects=projects,
    )


@router.get(
    "/employee-work-hours",
    response_model=EmployeeWorkHourReportListResponse,
    summary="员工工时报表",
    description=(
        "基于 employee_work_hours 查询员工工时；默认近 7 日。"
        "统计维度：detail（明细）、employee（按员工汇总）、"
        "employee_date（按员工+日期）、employee_month（按员工+月份）、"
        "project（按项目）、department（按部门）。"
        "明细 dimension 每行含 shift_type（班别：白班/晚班）。"
        "报表中心「员工工时报表」页使用本接口。"
    ),
)
def list_employee_work_hours_report(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    date_from: date | None = Query(None, description="报工日期起（含）"),
    date_to: date | None = Query(None, description="报工日期止（含）"),
    department: str | None = Query(None, description="部门（精确匹配）"),
    employee_no: str | None = Query(None, description="工号（精确匹配）"),
    project_name: str | None = Query(None, description="项目名称（精确匹配）"),
    shift_type: str | None = Query(
        None, description="班别（白班/晚班，或 day/night）"
    ),
    approval_status: str | None = Query(
        None, description="审批状态：pending / approved / rejected"
    ),
    dimension: str = Query("detail", description="统计维度"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dimension = _normalize_work_hour_dimension(dimension)
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=6)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    query = db.query(EmployeeWorkHour)
    query = _apply_work_hour_report_filters(
        query,
        date_from=date_from,
        date_to=date_to,
        department=department,
        employee_no=employee_no,
        project_name=project_name,
        approval_status=approval_status,
        shift_type=_normalize_shift_type_filter(shift_type),
    )
    all_items = _build_work_hour_report_items(query, dimension)
    total = len(all_items)
    work_hours_sum = round(sum(i.work_hours for i in all_items), 2)
    overtime_hours_sum = round(sum(i.overtime_hours for i in all_items), 2)
    start = (page - 1) * page_size
    page_items = all_items[start : start + page_size]

    return EmployeeWorkHourReportListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        dimension=dimension,
        work_hours_sum=work_hours_sum,
        overtime_hours_sum=overtime_hours_sum,
    )
