from typing import Literal

from datetime import date, datetime

from pydantic import BaseModel, Field

ENTERPRISE_CODES = ("江西中软", "前海中软", "测试企业")
EnterpriseCode = Literal["江西中软", "前海中软", "测试企业"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)
    enterprise_code: EnterpriseCode


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}


class DashboardStatItem(BaseModel):
    key: str
    label: str
    value: float | int
    unit: str = ""
    trend: str | None = None


class ProductionTrendPoint(BaseModel):
    date: str
    output: int


class WorkOrderStatusItem(BaseModel):
    status: str
    count: int


class TodoItem(BaseModel):
    id: int
    type: str
    title: str
    description: str
    priority: str
    link: str


class DashboardResponse(BaseModel):
    stats: list[DashboardStatItem]
    production_trend: list[ProductionTrendPoint]
    work_order_status: list[WorkOrderStatusItem]
    todos: list[TodoItem]


WorkOrderPriority = Literal["low", "normal", "high", "urgent"]


class WorkOrderCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=100)
    product_code: str = Field(min_length=1, max_length=50)
    production_line: str = Field(min_length=1, max_length=50)
    plan_quantity: int = Field(gt=0)
    priority: WorkOrderPriority = "normal"
    assignee: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date


class WorkOrderResponse(BaseModel):
    id: int
    order_no: str
    product_name: str
    product_code: str
    production_line: str
    plan_quantity: int
    priority: str
    assignee: str
    start_date: date
    end_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    page: int
    page_size: int
