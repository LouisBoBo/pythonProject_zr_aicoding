"""员工列表。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Employee, User

router = APIRouter(prefix="/api/employees", tags=["员工管理"])


class EmployeeListItem(BaseModel):
    """员工列表行，含部门、员工信息与工资。"""

    id: int = Field(description="员工 ID")
    employee_no: str = Field(description="工号")
    employee_name: str = Field(description="姓名")
    gender: str = Field(description="性别")
    phone: str | None = Field(default=None, description="手机号")
    position: str = Field(description="岗位")
    department_code: str = Field(description="部门编码")
    department_name: str = Field(description="部门名称")
    hire_date: date = Field(description="入职日期")
    status: str = Field(description="在职状态")
    salary: float = Field(description="月工资（元）")


class EmployeeListResponse(BaseModel):
    items: list[EmployeeListItem]
    total: int
    page: int
    page_size: int


def _to_item(row: Employee) -> EmployeeListItem:
    return EmployeeListItem(
        id=row.id,
        employee_no=row.employee_no,
        employee_name=row.employee_name,
        gender=row.gender,
        phone=row.phone,
        position=row.position,
        department_code=row.department_code,
        department_name=row.department_name,
        hire_date=row.hire_date,
        status=row.status,
        salary=float(row.salary or 0),
    )


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="员工列表",
    description="分页查询员工的部门、个人资料与月工资；员工列表页数据来自本接口。",
)
def list_employees(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    employee_no: str | None = Query(None, description="工号（模糊匹配）"),
    employee_name: str | None = Query(None, description="姓名（模糊匹配）"),
    department_name: str | None = Query(None, description="部门名称（模糊匹配）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Employee)
    if employee_no:
        query = query.filter(Employee.employee_no.ilike(f"%{employee_no.strip()}%"))
    if employee_name:
        query = query.filter(Employee.employee_name.ilike(f"%{employee_name.strip()}%"))
    if department_name:
        query = query.filter(Employee.department_name.ilike(f"%{department_name.strip()}%"))

    total = query.count()
    rows = (
        query.order_by(Employee.department_code.asc(), Employee.employee_no.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return EmployeeListResponse(
        items=[_to_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
