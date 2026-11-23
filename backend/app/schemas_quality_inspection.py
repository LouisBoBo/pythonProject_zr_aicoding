"""品质检验记录 / 检验任务 API Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class QualityInspectionRecordResponse(BaseModel):
    """检验记录列表行（含 IPQC 源表全字段）"""

    id: int
    inspection_no: str
    inspection_type: str
    inspection_result: str
    status: str = "pending"
    work_order_id: int | None = None
    work_order_no: str | None = None
    product_code: str | None = None
    batch_no: str | None = None
    material_id: int | None = None
    material_code: str | None = None
    material_name: str | None = None
    inspector: str
    inspected_at: datetime
    non_conforming_qty: int
    remark: str | None = None
    # IPQC 全字段
    source_cid: str | None = None
    source_created_at: datetime | None = None
    source_user_created: str | None = None
    source_modified_at: datetime | None = None
    source_user_modified: str | None = None
    source_state: str | None = None
    instance_id: str | None = None
    row_remark: str | None = None
    enterprise_code: str | None = None
    org_code: str | None = None
    inspect_code: str | None = None
    source_inspect_type: int | None = None
    template_id: str | None = None
    process_id: str | None = None
    process_name: str | None = None
    scan_barcode: str | None = None
    item_id: str | None = None
    submit_qty: float | None = None
    inspected_qty: int | None = None
    unit: str | None = None
    shift: str | None = None
    is_lab: str | None = None
    lab_receive_time: datetime | None = None
    lab_receive_user_name: str | None = None
    lab_inspect_time: datetime | None = None
    lab_inspect_user_name: str | None = None
    check_time: datetime | None = None
    check_user_name: str | None = None
    check_remark: str | None = None
    source_result: int | None = None
    source_status: int | None = None
    lab_inspect_remark: str | None = None
    ng_disposal: str | None = None
    customer_code: str | None = None
    mo_lot: str | None = None
    decision_mode: int | None = None
    come_in_time: datetime | None = None
    inspect_count: int | None = None
    source_pid: str | None = None
    is_reinspection: int = 0
    ipqc_entry_type: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityInspectionImportResult(BaseModel):
    """IPQC Excel 导入结果"""

    created: int = Field(..., description="新写入条数")
    updated: int = Field(0, description="按 CID 全量更新条数")
    skipped: int = Field(..., description="跳过条数（已删除等）")
    pending_count: int = Field(0, description="本批中待审核任务数")
    failed_count: int = Field(0, description="本批中不合格条数")
    errors: list[str] = Field(default_factory=list, description="行级错误（最多 50 条）")


class QualityInspectionRecordListResponse(BaseModel):
    """检验记录分页列表"""

    items: list[QualityInspectionRecordResponse]
    total: int
    page: int
    page_size: int


class QualityInspectionTaskResponse(BaseModel):
    """检验任务列表行"""

    id: int
    inspection_no: str
    inspection_type: str
    status: str
    work_order_no: str | None = None
    product_code: str | None = None
    batch_no: str | None = None
    material_code: str | None = None
    material_name: str | None = None
    inspector: str
    inspected_at: datetime
    remark: str | None = None
    process_id: str | None = None
    process_name: str | None = None
    template_id: str | None = None
    customer_code: str | None = None
    shift: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityInspectionTaskListResponse(BaseModel):
    """检验任务分页列表"""

    items: list[QualityInspectionTaskResponse]
    total: int
    page: int
    page_size: int


class QualityInspectionTaskStatusUpdate(BaseModel):
    """检验任务状态流转"""

    status: str = Field(..., pattern="^(passed|failed)$", description="目标状态：passed 合格 / failed 不合格")


class IpqcProcessYieldItem(BaseModel):
    """工序合格率"""

    process_id: str | None = None
    process_name: str | None = None
    total: int
    pass_count: int
    fail_count: int
    pending_count: int
    pass_rate: float = Field(..., description="合格率%（不含待审）")
    fail_rate: float = Field(..., description="不合格率%（不含待审）")


class IpqcDailyTrendItem(BaseModel):
    """日不合格率趋势"""

    date: str
    total: int
    pass_count: int
    fail_count: int
    pending_count: int
    fail_rate: float = Field(..., description="不合格率%（不含待审）")


class IpqcCustomerFailItem(BaseModel):
    """客户不合格排行"""

    customer_code: str
    total: int
    fail_count: int
    fail_rate: float


class IpqcCheckLagBucket(BaseModel):
    """审核时效分桶"""

    label: str
    count: int


class IpqcCheckLagStats(BaseModel):
    """待审积压 + 审核时效"""

    pending_count: int
    checked_count: int
    avg_hours: float | None = None
    median_hours: float | None = None
    p75_hours: float | None = None
    over_24h_count: int = 0
    over_24h_ratio: float = 0.0
    buckets: list[IpqcCheckLagBucket] = Field(default_factory=list)


class IpqcAnalyticsSummary(BaseModel):
    """IPQC 分析摘要"""

    total: int
    pass_count: int
    fail_count: int
    pending_count: int
    pass_rate: float
    fail_rate: float


class IpqcAnalyticsResponse(BaseModel):
    """IPQC 四维分析一页数据"""

    summary: IpqcAnalyticsSummary
    process_yield: list[IpqcProcessYieldItem]
    daily_trend: list[IpqcDailyTrendItem]
    customer_fail_top: list[IpqcCustomerFailItem]
    check_lag: IpqcCheckLagStats
