from typing import Literal

from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field

from app.message_utils import message_level_from_category

ENTERPRISE_CODES = ("江西中软", "江西中软电子有限公司", "前海中软", "测试企业")
EnterpriseCode = Literal["江西中软", "江西中软电子有限公司", "前海中软", "测试企业"]


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
WorkOrderStatus = Literal["pending", "in_progress", "completed", "closed", "cancelled"]


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
    current_process: str | None = Field(default=None, max_length=50, description="当前工序")


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
    current_process: str | None = Field(default=None, max_length=50)


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
    actual_start_time: datetime | None
    actual_end_time: datetime | None = Field(default=None, description="实际结束时间")
    end_date: date | None
    current_process: str | None = Field(default=None, description="当前工序")
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderListResponse(BaseModel):
    items: list[WorkOrderResponse]
    total: int
    page: int
    page_size: int


class WipReportItem(BaseModel):
    """在制品报表行：按工单维度。"""

    id: int
    order_no: str = Field(description="工单号")
    product_name: str = Field(description="品名")
    current_process: str | None = Field(default=None, description="当前工序（贴片/焊接/AOI检测/功能测试/包装）")
    wip_quantity: int = Field(description="在制数量（wip 口径：计划数量 - 实际数量）")
    status: str = Field(description="工单状态")
    start_date: date | None = Field(default=None, description="计划开始日期")
    end_date: date | None = Field(default=None, description="计划结束日期")
    plan_quantity: int = Field(description="计划数量")
    actual_quantity: int = Field(description="实际数量")

    model_config = {"from_attributes": True}


class WipReportListResponse(BaseModel):
    items: list[WipReportItem]
    total: int
    page: int
    page_size: int
    metric: str = Field(default="wip", description="指标口径标识")


class WipReportProcessesResponse(BaseModel):
    processes: list[str] = Field(description="可选工序列表（用于筛选）")


class DailyOutputReportItem(BaseModel):
    """日产报表行：按日期 / 产线 / 产品聚合。"""

    report_date: date = Field(description="生产日期")
    production_line: str = Field(description="产线名称")
    product_code: str | None = Field(default=None, description="产品编码")
    product_name: str | None = Field(default=None, description="产品名称")
    plan_qty: int = Field(description="计划产量")
    actual_qty: int = Field(description="实际产量")
    defect_qty: int = Field(description="不良数量")
    area_output: float = Field(description="面积产出")
    achievement_rate: float = Field(description="达成率（%），计划为 0 时为 0")
    defect_rate: float = Field(description="不良率（%），产量为 0 时为 0")


class DailyOutputReportListResponse(BaseModel):
    items: list[DailyOutputReportItem]
    total: int
    page: int
    page_size: int
    plan_qty_sum: int = Field(description="当前筛选条件下计划产量合计")
    actual_qty_sum: int = Field(description="当前筛选条件下实际产量合计")
    defect_qty_sum: int = Field(description="当前筛选条件下不良数量合计")


class DailyOutputLinesResponse(BaseModel):
    lines: list[str] = Field(description="可选产线名称列表（用于筛选）")


class EmployeeWorkHourReportItem(BaseModel):
    """员工工时报表行。"""

    employee_name: str = Field(description="员工姓名")
    employee_no: str = Field(description="工号")
    department: str = Field(description="所属部门")
    project_name: str | None = Field(default=None, description="项目名称")
    task_name: str | None = Field(default=None, description="任务名称")
    work_date: date | None = Field(default=None, description="日期")
    work_month: str | None = Field(default=None, description="月份（YYYY-MM）")
    work_hours: float = Field(description="工时数")
    overtime_hours: float = Field(description="加班工时")
    approval_status: str | None = Field(default=None, description="审批/状态")
    record_count: int | None = Field(default=None, description="明细条数（汇总维度）")


class EmployeeWorkHourReportListResponse(BaseModel):
    items: list[EmployeeWorkHourReportItem]
    total: int
    page: int
    page_size: int
    dimension: str = Field(description="统计维度")
    work_hours_sum: float = Field(description="工时合计")
    overtime_hours_sum: float = Field(description="加班工时合计")


class EmployeeWorkHourFilterEmployee(BaseModel):
    employee_no: str
    employee_name: str


class EmployeeWorkHourFiltersResponse(BaseModel):
    departments: list[str] = Field(description="部门选项")
    employees: list[EmployeeWorkHourFilterEmployee] = Field(description="员工选项")
    projects: list[str] = Field(description="项目选项")


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


# --- Equipment Ledger ---

EquipmentStatus = Literal["运行", "停机", "维修", "报废"]


class EquipmentCreate(BaseModel):
    equipment_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    spec_model: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=100)
    status: EquipmentStatus = "运行"
    purchase_date: date | None = None
    commission_date: date | None = None
    supplier: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)


class EquipmentUpdate(BaseModel):
    equipment_code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    spec_model: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=100)
    status: EquipmentStatus | None = None
    purchase_date: date | None = None
    commission_date: date | None = None
    supplier: str | None = Field(default=None, max_length=100)
    remark: str | None = Field(default=None, max_length=500)


class EquipmentResponse(BaseModel):
    id: int
    equipment_code: str
    name: str
    spec_model: str | None
    department: str | None
    location: str | None
    status: str
    purchase_date: date | None
    commission_date: date | None
    supplier: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    page: int
    page_size: int


class EquipmentImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


# --- Equipment Maintenance ---

MaintenanceCycleType = Literal["day", "week", "month", "runtime"]
MaintenancePlanStatus = Literal["enabled", "disabled"]
MaintenanceOrderStatus = Literal["pending", "in_progress", "completed", "closed"]


class MaintenanceItemStandard(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    check_method: str = Field(min_length=1, max_length=200)
    standard: str = Field(min_length=1, max_length=200)


class MaintenanceResultItem(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    check_method: str | None = Field(default=None, max_length=200)
    standard: str | None = Field(default=None, max_length=200)
    result: str = Field(min_length=1, max_length=200)
    remark: str | None = Field(default=None, max_length=500)


class EquipmentMaintenancePlanCreate(BaseModel):
    equipment_id: int
    name: str = Field(min_length=1, max_length=100)
    cycle_type: MaintenanceCycleType = "day"
    cycle_value: int = Field(default=1, ge=1)
    items: list[MaintenanceItemStandard] = Field(default_factory=list)
    status: MaintenancePlanStatus = "enabled"


class EquipmentMaintenancePlanUpdate(BaseModel):
    equipment_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    cycle_type: MaintenanceCycleType | None = None
    cycle_value: int | None = Field(default=None, ge=1)
    items: list[MaintenanceItemStandard] | None = None
    status: MaintenancePlanStatus | None = None


class EquipmentMaintenancePlanResponse(BaseModel):
    id: int
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    name: str
    cycle_type: str
    cycle_value: int
    items: list[MaintenanceItemStandard]
    status: str
    next_due_at: datetime | None
    alert_level: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentMaintenancePlanListResponse(BaseModel):
    items: list[EquipmentMaintenancePlanResponse]
    total: int
    page: int
    page_size: int


class EquipmentMaintenanceOrderCreate(BaseModel):
    plan_id: int | None = None
    equipment_id: int
    planned_start_at: datetime
    plan_complete_date: date | None = Field(default=None, description="计划完成时间（仅日期）")
    assignee: str | None = Field(default=None, max_length=50)
    remark: str | None = Field(default=None, max_length=500)


class EquipmentMaintenanceOrderUpdate(BaseModel):
    plan_id: int | None = None
    equipment_id: int | None = None
    planned_start_at: datetime | None = None
    plan_complete_date: date | None = Field(default=None, description="计划完成时间（仅日期）")
    assignee: str | None = Field(default=None, max_length=50)
    remark: str | None = Field(default=None, max_length=500)
    status: MaintenanceOrderStatus | None = None


class EquipmentMaintenanceOrderDispatch(BaseModel):
    assignee: str = Field(min_length=1, max_length=50)
    planned_start_at: datetime | None = None


class EquipmentMaintenanceOrderExecute(BaseModel):
    executor: str = Field(min_length=1, max_length=50)
    results: list[MaintenanceResultItem] = Field(default_factory=list)
    remark: str | None = Field(default=None, max_length=500)


class EquipmentMaintenanceOrderResponse(BaseModel):
    id: int
    plan_id: int | None
    plan_name: str | None = None
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    order_no: str
    status: str
    assignee: str | None
    planned_start_at: datetime
    plan_complete_date: date | None = Field(default=None, description="计划完成时间（仅日期）")
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    executor: str | None
    results: list[MaintenanceResultItem] | None = None
    remark: str | None
    alert_level: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentMaintenanceOrderListResponse(BaseModel):
    items: list[EquipmentMaintenanceOrderResponse]
    total: int
    page: int
    page_size: int


class MaintenanceAlertItem(BaseModel):
    id: int
    type: str
    name: str
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    due_at: datetime | None = None
    alert_level: str


class MaintenanceAlertsResponse(BaseModel):
    due_soon: list[MaintenanceAlertItem]
    overdue: list[MaintenanceAlertItem]


class EquipmentMaintenanceStatusResponse(BaseModel):
    equipment_id: int
    status_label: str
    alert_level: str
    active_plans: int
    pending_orders: int
    next_due_at: datetime | None = None


# --- Equipment Repair ---

RepairUrgency = Literal["low", "normal", "high", "urgent"]
RepairStatus = Literal["pending", "in_progress", "completed", "closed"]

FAULT_CATEGORIES = [
    "机械故障", "电气故障", "液压故障", "气动故障",
    "控制系统故障", "传动故障", "润滑故障", "其他",
]


class EquipmentRepairPartCreate(BaseModel):
    part_name: str = Field(min_length=1, max_length=100)
    part_spec: str | None = Field(default=None, max_length=100)
    quantity: int = Field(default=1, ge=1)
    unit: str = Field(default="个", max_length=20)
    unit_price: float = Field(default=0, ge=0)


class EquipmentRepairPartResponse(BaseModel):
    id: int
    repair_id: int
    part_name: str
    part_spec: str | None
    quantity: int
    unit: str
    unit_price: float

    model_config = {"from_attributes": True}


class EquipmentRepairCreate(BaseModel):
    equipment_id: int
    fault_category: str = Field(default="机械故障", max_length=50)
    fault_description: str = Field(min_length=1, max_length=2000)
    urgency: RepairUrgency = "normal"
    reporter: str = Field(min_length=1, max_length=50)
    images: list[str] | None = Field(default=None)


class EquipmentRepairUpdate(BaseModel):
    equipment_id: int | None = None
    fault_category: str | None = Field(default=None, max_length=50)
    fault_description: str | None = Field(default=None, min_length=1, max_length=2000)
    urgency: RepairUrgency | None = None
    status: RepairStatus | None = None
    reporter: str | None = Field(default=None, min_length=1, max_length=50)
    repair_person: str | None = Field(default=None, max_length=50)
    repair_description: str | None = Field(default=None, max_length=2000)
    repair_completed_at: datetime | None = Field(default=None, description="维修完成时间")
    images: list[str] | None = None
    parts: list[EquipmentRepairPartCreate] | None = None


class EquipmentRepairListItem(BaseModel):
    id: int
    repair_no: str
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    fault_category: str
    fault_description: str
    urgency: str
    status: str
    reporter: str
    repair_person: str | None
    repair_completed_at: datetime | None = Field(default=None, description="维修完成时间")
    created_at: datetime

    model_config = {"from_attributes": True}


class EquipmentRepairListResponse(BaseModel):
    items: list[EquipmentRepairListItem]
    total: int
    page: int
    page_size: int


class EquipmentRepairDetail(BaseModel):
    id: int
    repair_no: str
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    fault_category: str
    fault_description: str
    urgency: str
    status: str
    reporter: str
    repair_person: str | None
    start_time: datetime | None
    repair_completed_at: datetime | None = Field(default=None, description="维修完成时间")
    repair_description: str | None
    images: list[str] | None
    parts: list[EquipmentRepairPartResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QualityKpiItem(BaseModel):
    key: str
    label: str
    value: float
    unit: str = "%"
    change: float | None = None
    change_direction: str | None = None


class QualityKpiResponse(BaseModel):
    period: str
    items: list[QualityKpiItem]


class QualityTrendPoint(BaseModel):
    label: str
    yield_rate: float
    defect_rate: float


class QualityTrendResponse(BaseModel):
    granularity: str
    points: list[QualityTrendPoint]


class QualityProcessYieldItem(BaseModel):
    process: str
    yield_rate: float
    total_inspected: int


class QualityProcessYieldResponse(BaseModel):
    items: list[QualityProcessYieldItem]


class QualityDefectDistributionItem(BaseModel):
    name: str
    value: int


class QualityDefectDistributionResponse(BaseModel):
    by: str
    items: list[QualityDefectDistributionItem]


class QualityAnomalyItem(BaseModel):
    id: int
    production_line: str
    process: str
    defect_type: str
    severity: str
    status: str
    discovered_at: datetime
    handler: str | None = None


class QualityAnomalyListResponse(BaseModel):
    items: list[QualityAnomalyItem]
    total: int
    page: int | None = None
    page_size: int | None = None


class QualityTopDefectItem(BaseModel):
    rank: int
    defect_type: str
    production_line: str
    process: str
    product_code: str
    quantity: int


class QualityTopDefectResponse(BaseModel):
    items: list[QualityTopDefectItem]


# ============================================================
#  Device Dashboard (设备看板)
# ============================================================

class DeviceStatusSummaryItem(BaseModel):
    status: str
    count: int
    percent: float
    color: str


class DeviceStatusSummaryResponse(BaseModel):
    items: list[DeviceStatusSummaryItem]
    total: int


class DeviceOEEResponse(BaseModel):
    availability: float
    performance: float
    quality: float
    oee: float


class DeviceDashboardListItem(BaseModel):
    code: str
    name: str
    status: str
    runtime_hours: float
    last_alarm: str | None = None


class DeviceDashboardListResponse(BaseModel):
    items: list[DeviceDashboardListItem]
    total: int
    page: int
    page_size: int


class DeviceUtilizationPoint(BaseModel):
    label: str
    value: float


class DeviceUtilizationResponse(BaseModel):
    period: str
    labels: list[str]
    values: list[float]


class DeviceAlarmTypeItem(BaseModel):
    name: str
    value: int


class DeviceAlarmTrendResponse(BaseModel):
    labels: list[str]
    values: list[int]
    type_distribution: list[DeviceAlarmTypeItem]


class DeviceOutputItem(BaseModel):
    code: str
    name: str
    today_output: int
    week_output: int


class DeviceOutputResponse(BaseModel):
    items: list[DeviceOutputItem]


# ============================================================
#  Comprehensive Kanban (综合看板)
# ============================================================

class CompKanbanLineStatus(BaseModel):
    line_name: str
    in_production: int
    completed: int
    pending: int


class CompKanbanTrendPoint(BaseModel):
    label: str
    value: float


class CompKanbanProductionProgress(BaseModel):
    active_orders: int
    completion_rate: float
    schedule_achievement_trend: list[CompKanbanTrendPoint]
    line_status: list[CompKanbanLineStatus]


class CompKanbanDefectItem(BaseModel):
    name: str
    value: int


class CompKanbanQualityOverview(BaseModel):
    yield_trend: list[CompKanbanTrendPoint]
    yield_target: float
    first_pass_rate: float
    defect_distribution: list[CompKanbanDefectItem]


class CompKanbanDeviceCard(BaseModel):
    code: str
    name: str
    utilization: float
    status: str


class CompKanbanStatusPie(BaseModel):
    name: str
    value: int
    color: str


class CompKanbanDeviceAlert(BaseModel):
    id: int
    device_code: str
    device_name: str
    alert_type: str
    severity: str
    time: str
    description: str


class CompKanbanDeviceMonitor(BaseModel):
    devices: list[CompKanbanDeviceCard]
    status_distribution: list[CompKanbanStatusPie]
    alerts: list[CompKanbanDeviceAlert]


class CompKanbanOverdueOrder(BaseModel):
    order_no: str
    customer: str
    overdue_days: int
    status: str


class CompKanbanShipmentStats(BaseModel):
    this_week: int
    this_month: int


class CompKanbanOrderDelivery(BaseModel):
    delivery_rate: float
    monthly_trend: list[CompKanbanTrendPoint]
    overdue_orders: list[CompKanbanOverdueOrder]
    shipment_stats: CompKanbanShipmentStats


class CompKanbanMaterialItem(BaseModel):
    name: str
    current_stock: float
    safety_line: float
    max_stock: float
    status: str  # normal / warning / shortage


class CompKanbanMaterialInventory(BaseModel):
    critical_materials: list[CompKanbanMaterialItem]
    shortage_alerts: list[str]
    turnover_days_trend: list[CompKanbanTrendPoint]


class ComprehensiveKanbanResponse(BaseModel):
    production_progress: CompKanbanProductionProgress
    quality_overview: CompKanbanQualityOverview
    device_monitor: CompKanbanDeviceMonitor
    order_delivery: CompKanbanOrderDelivery
    material_inventory: CompKanbanMaterialInventory


# ============================================================
#  Warehouse Dashboard (仓储看板)
# ============================================================


class WarehouseKpiCard(BaseModel):
    key: str
    label: str
    value: str
    unit: str
    sub: str
    color: str


class WarehouseTrendSeries(BaseModel):
    labels: list[str]
    values: list[int]
    summary: int


class WarehouseTrendBundle(BaseModel):
    today: WarehouseTrendSeries
    week: WarehouseTrendSeries
    month: WarehouseTrendSeries


class WarehouseAlertItem(BaseModel):
    level: str
    text: str


class WarehouseLocationSlice(BaseModel):
    name: str
    value: int
    color: str


class WarehouseActivityItem(BaseModel):
    time: str
    type: str
    typeLabel: str
    text: str


class WarehouseMaterialRow(BaseModel):
    material_code: str
    material_name: str
    category: str
    spec: str | None = None
    unit: str
    stock_qty: int
    safety_stock: int
    location_code: str | None = None
    last_update: str


class WarehouseDashboardResponse(BaseModel):
    kpi_cards: list[WarehouseKpiCard]
    inbound: WarehouseTrendBundle
    outbound: WarehouseTrendBundle
    alerts: list[WarehouseAlertItem]
    location_distribution: list[WarehouseLocationSlice]
    activities: list[WarehouseActivityItem]
    materials: list[WarehouseMaterialRow]
    categories: list[str]


class InventoryStockResponse(BaseModel):
    """物料库存列表行"""

    id: int
    material_id: int
    material_code: str
    material_name: str
    warehouse_id: int
    warehouse_name: str
    quantity: int
    unit: str
    safety_stock: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryStockListResponse(BaseModel):
    """物料库存分页列表"""

    items: list[InventoryStockResponse]
    total: int
    page: int
    page_size: int
    quantity_sum: int


class WarehouseOption(BaseModel):
    """仓库下拉选项"""

    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class MaterialOption(BaseModel):
    """物料下拉选项（入库表单）"""

    id: int
    material_code: str
    material_name: str
    spec: str | None = None
    unit: str

    model_config = {"from_attributes": True}


class WarehouseLocationOption(BaseModel):
    """库位下拉选项"""

    id: int
    location_code: str
    warehouse_id: int
    warehouse_name: str
    status: str

    model_config = {"from_attributes": True}


class MaterialInboundResponse(BaseModel):
    """物料入库列表行"""

    id: int
    inbound_no: str
    material_id: int
    material_code: str
    material_name: str
    spec: str | None = None
    quantity: int
    unit: str
    warehouse_id: int
    warehouse_name: str
    location_id: int | None = None
    location_code: str | None = None
    inbound_date: date
    handler: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialInboundListResponse(BaseModel):
    """物料入库分页列表"""

    items: list[MaterialInboundResponse]
    total: int
    page: int
    page_size: int


class MaterialInboundCreate(BaseModel):
    """新增物料入库"""

    material_id: int
    quantity: int
    warehouse_id: int
    location_id: int | None = None
    inbound_date: date
    handler: str | None = None
    status: str = "completed"


MessageLevel = Literal["high", "medium", "low"]
MessageCategory = Literal["system", "alert", "announcement"]
MessagePriority = Literal["normal", "high", "urgent"]


class MessageCreate(BaseModel):
    """新建消息"""

    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: MessageCategory = "system"
    priority: MessagePriority = "normal"
    source: str | None = Field(None, max_length=50)
    link: str | None = Field(None, max_length=200)


class MessageUpdate(BaseModel):
    """更新消息"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1)
    category: MessageCategory | None = None
    priority: MessagePriority | None = None
    source: str | None = Field(None, max_length=50)
    link: str | None = Field(None, max_length=200)


class MessageResponse(BaseModel):
    """消息列表行"""

    id: int
    title: str
    content: str
    category: str
    priority: str
    source: str | None = None
    link: str | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def level(self) -> MessageLevel:
        """按消息类型映射等级：业务告警=高，系统通知=中，公告通知=低。"""
        return message_level_from_category(self.category)  # type: ignore[return-value]


class MessageListResponse(BaseModel):
    """消息分页列表"""

    items: list[MessageResponse]
    total: int
    page: int
    size: int


class MessageUnreadCountResponse(BaseModel):
    """未读消息数量"""

    count: int


class MessageStatsResponse(BaseModel):
    """消息未读统计"""

    total: int
    system: int
    alert: int
    announcement: int
