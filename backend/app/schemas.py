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


class WorkOrderUpdate(BaseModel):
    order_no: str | None = Field(default=None, min_length=1, max_length=50)
    product_name: str | None = Field(default=None, min_length=1, max_length=100)
    product_code: str | None = Field(default=None, max_length=50)
    production_line: str | None = Field(default=None, max_length=50)
    plan_quantity: int | None = Field(default=None, gt=0)
    actual_quantity: int | None = Field(default=None, ge=0)
    priority: WorkOrderPriority | None = None
    assignee: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    remark: str | None = Field(default=None, max_length=500)


class WorkOrderStatusUpdate(BaseModel):
    status: WorkOrderStatus


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


KanbanBoardCategory = Literal["production", "quality", "equipment", "warehouse", "general"]
KanbanBoardStatus = Literal["draft", "active", "archived"]


class KanbanBoardCreate(BaseModel):
    board_code: str = Field(min_length=1, max_length=50)
    board_name: str = Field(min_length=1, max_length=100)
    category: KanbanBoardCategory = "production"
    production_line: str | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    refresh_interval: int = Field(default=60, ge=10, le=3600)
    remark: str | None = Field(default=None, max_length=500)


class KanbanBoardUpdate(BaseModel):
    board_code: str | None = Field(default=None, min_length=1, max_length=50)
    board_name: str | None = Field(default=None, min_length=1, max_length=100)
    category: KanbanBoardCategory | None = None
    production_line: str | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    refresh_interval: int | None = Field(default=None, ge=10, le=3600)
    remark: str | None = Field(default=None, max_length=500)


class KanbanBoardStatusUpdate(BaseModel):
    status: KanbanBoardStatus


class KanbanBoardResponse(BaseModel):
    id: int
    board_code: str
    board_name: str
    category: str
    status: str
    production_line: str | None
    owner: str | None
    description: str | None
    refresh_interval: int
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KanbanBoardListResponse(BaseModel):
    items: list[KanbanBoardResponse]
    total: int
    page: int
    page_size: int


class ProductionStatsRow(BaseModel):
    time: str
    today_completed: int
    today_area_output: float
    today_defect_total: int
    daily_defect_rate: str
    today_incoming_boards: int


class ProductionDetailRow(BaseModel):
    time: str
    process_card_no: str
    product_model: str
    quantity: int
    today_completed: int
    total_completed: int


class CompletionChartPoint(BaseModel):
    label: str
    lot_output: int
    model_output: int


class ProductionKanbanDashboard(BaseModel):
    board_category: str
    display_time: str
    weekday: str
    achievement_rate: float
    production_area: float
    stats_rows: list[ProductionStatsRow]
    detail_rows: list[ProductionDetailRow]
    completion_chart: list[CompletionChartPoint]


class ProductionStatTrend(BaseModel):
    direction: str
    text: str


class ProductionOverviewStats(BaseModel):
    today_completed: int
    today_area_output: float
    today_defect_total: int
    daily_defect_rate: str
    today_incoming_boards: int
    trends: dict[str, ProductionStatTrend]


class ProductionOverviewResponse(BaseModel):
    achievement_rate: float
    production_area: float
    kpi_trends: dict[str, ProductionStatTrend]
    stats: ProductionOverviewStats
    completion_chart: list[CompletionChartPoint]
    detail_rows: list[ProductionDetailRow]


# --- Device ---

class DeviceTypeResponse(BaseModel):
    id: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class DeviceResponse(BaseModel):
    id: int
    code: str
    name: str
    device_type_id: int
    device_type_name: str | None = None
    location: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    total: int
    page: int
    page_size: int


# --- Inspection ---

InspectionFrequencyType = Literal["daily", "weekly", "monthly", "custom"]
InspectionJudgeType = Literal["ok_ng", "numeric"]
InspectionRecordStatus = Literal["normal", "abnormal", "draft", "incomplete"]


class InspectionPlanItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    standard_value: str | None = Field(default=None, max_length=100)
    judge_type: InspectionJudgeType = "ok_ng"
    sort_order: int = 0


class InspectionPlanItemResponse(BaseModel):
    id: int
    plan_id: int
    item_name: str
    standard_value: str | None
    judge_type: str
    sort_order: int

    model_config = {"from_attributes": True}


class InspectionPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    device_type_id: int | None = None
    device_id: int | None = None
    frequency_type: InspectionFrequencyType = "daily"
    frequency_value: int | None = None
    cron_expr: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    items: list[InspectionPlanItemCreate] = Field(default_factory=list)


class InspectionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    device_type_id: int | None = None
    device_id: int | None = None
    frequency_type: InspectionFrequencyType | None = None
    frequency_value: int | None = None
    cron_expr: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    items: list[InspectionPlanItemCreate] | None = None


class InspectionPlanResponse(BaseModel):
    id: int
    name: str
    device_type_id: int | None
    device_id: int | None
    device_type_name: str | None = None
    device_name: str | None = None
    frequency_type: str
    frequency_value: int | None
    cron_expr: str | None
    is_active: bool
    last_executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[InspectionPlanItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InspectionPlanListResponse(BaseModel):
    items: list[InspectionPlanResponse]
    total: int
    page: int
    page_size: int


class InspectionRecordItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    standard_value: str | None = Field(default=None, max_length=100)
    actual_value: str | None = Field(default=None, max_length=100)
    result: str | None = Field(default=None, max_length=10)
    remark: str | None = Field(default=None, max_length=500)


class InspectionRecordItemResponse(BaseModel):
    id: int
    record_id: int
    item_name: str
    standard_value: str | None
    actual_value: str | None
    result: str | None
    remark: str | None

    model_config = {"from_attributes": True}


class InspectionRecordCreate(BaseModel):
    device_id: int
    plan_id: int | None = None
    inspector: str = Field(min_length=1, max_length=50)
    inspect_date: date
    status: InspectionRecordStatus = "draft"
    remark: str | None = None
    items: list[InspectionRecordItemCreate] = Field(default_factory=list)


class InspectionRecordUpdate(BaseModel):
    device_id: int | None = None
    plan_id: int | None = None
    inspector: str | None = Field(default=None, min_length=1, max_length=50)
    inspect_date: date | None = None
    status: InspectionRecordStatus | None = None
    remark: str | None = None
    items: list[InspectionRecordItemCreate] | None = None


class InspectionRecordResponse(BaseModel):
    id: int
    device_id: int
    device_code: str | None = None
    device_name: str | None = None
    plan_id: int | None
    plan_name: str | None = None
    inspector: str
    inspect_date: date
    status: str
    remark: str | None
    created_at: datetime
    items: list[InspectionRecordItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InspectionRecordListResponse(BaseModel):
    items: list[InspectionRecordResponse]
    total: int
    page: int
    page_size: int


class InspectionTrendPoint(BaseModel):
    date: str
    rate: float


class InspectionTypeRate(BaseModel):
    device_type: str
    rate: float
    total: int
    completed: int


class InspectionAbnormalBrief(BaseModel):
    id: int
    device_code: str
    device_name: str
    inspect_date: date
    inspector: str
    remark: str | None


class InspectionDashboardStats(BaseModel):
    today_due: int
    today_completed: int
    today_abnormal: int
    completion_rate: float
    trend: list[InspectionTrendPoint]
    type_rates: list[InspectionTypeRate]
    recent_abnormals: list[InspectionAbnormalBrief]
