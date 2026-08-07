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


class AnomalySegment(BaseModel):
    name: str
    value: int


class HourlyStats(BaseModel):
    production_time: str
    daily_output: int
    daily_avg: int


class ManufacturingDashboard(BaseModel):
    display_date: str
    monthly_output: int
    last_month_output: int
    daily_current: int
    daily_target: int
    efficiency_count: int
    efficiency_rate: int
    efficiency_trend: list[int]
    anomaly_percent: int
    anomaly_segments: list[AnomalySegment]
    production_trend_value: float
    production_trend: list[int]
    hourly_avg: float
    hourly_bars: list[int]
    hourly_output_trend: list[int]
    hourly_stats: HourlyStats


class DashboardResponse(BaseModel):
    stats: list[DashboardStatItem]
    production_trend: list[ProductionTrendPoint]
    work_order_status: list[WorkOrderStatusItem]
    todos: list[TodoItem]
    manufacturing: ManufacturingDashboard


WorkOrderPriority = Literal["low", "normal", "high", "urgent"]
WorkOrderStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class WorkOrderCreate(BaseModel):
    order_no: str = Field(min_length=1, max_length=50)
    product_name: str = Field(min_length=1, max_length=100)
    product_code: str | None = Field(default=None, max_length=50)
    production_line: str | None = Field(default=None, max_length=50)
    plan_quantity: int = Field(gt=0)
    priority: WorkOrderPriority = "normal"
    assignee: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    remark: str | None = Field(default=None, max_length=500)


class WorkOrderResponse(BaseModel):
    id: int
    order_no: str
    product_name: str
    product_code: str | None
    production_line: str | None
    plan_quantity: int
    actual_quantity: int
    status: str
    priority: str
    assignee: str | None
    start_date: date | None
    end_date: date | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    page: int
    page_size: int
