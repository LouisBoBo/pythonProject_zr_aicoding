"""IPQC API Schema（与品质检验记录联动）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class IpqcTestItemCreate(BaseModel):
    item_code: str = Field(..., min_length=1, max_length=50, description="项目编码")
    item_name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    category: str | None = Field(None, max_length=50, description="分类")
    standard_value: str | None = Field(None, max_length=200, description="标准值")
    judge_type: str = Field("ok_ng", pattern="^(ok_ng|numeric)$", description="判定类型")
    unit: str | None = Field(None, max_length=20, description="单位")
    process_name: str | None = Field(None, max_length=50, description="适用工序")
    remark: str | None = Field(None, max_length=2000, description="备注")


class IpqcTestItemUpdate(BaseModel):
    item_name: str | None = Field(None, min_length=1, max_length=100, description="项目名称")
    category: str | None = Field(None, max_length=50, description="分类")
    standard_value: str | None = Field(None, max_length=200, description="标准值")
    judge_type: str | None = Field(None, pattern="^(ok_ng|numeric)$", description="判定类型")
    unit: str | None = Field(None, max_length=20, description="单位")
    process_name: str | None = Field(None, max_length=50, description="适用工序")
    status: str | None = Field(None, pattern="^(active|disabled)$", description="状态")
    remark: str | None = Field(None, max_length=2000, description="备注")


class IpqcTestItemResponse(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: str | None = None
    standard_value: str | None = None
    judge_type: str
    unit: str | None = None
    process_name: str | None = None
    status: str
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IpqcTestItemListResponse(BaseModel):
    items: list[IpqcTestItemResponse]
    total: int
    page: int
    page_size: int


class IpqcTemplateItemIn(BaseModel):
    test_item_id: int = Field(..., description="测试项目 ID")
    sort_order: int = Field(0, description="排序")
    required: bool = Field(True, description="是否必检")


class IpqcTemplateCreate(BaseModel):
    template_code: str = Field(..., min_length=1, max_length=40, description="模板编码（对齐源 CTEMPLATE_ID）")
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    process_id: str | None = Field(None, max_length=40, description="工序 ID")
    process_name: str | None = Field(None, max_length=50, description="工序名称")
    remark: str | None = Field(None, max_length=2000, description="备注")
    items: list[IpqcTemplateItemIn] = Field(default_factory=list, description="关联检验项目")


class IpqcTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100, description="模板名称")
    process_id: str | None = Field(None, max_length=40, description="工序 ID")
    process_name: str | None = Field(None, max_length=50, description="工序名称")
    status: str | None = Field(None, pattern="^(active|disabled)$", description="状态")
    remark: str | None = Field(None, max_length=2000, description="备注")
    items: list[IpqcTemplateItemIn] | None = Field(None, description="若传入则整体替换关联项目并升版")
    change_note: str | None = Field(None, max_length=500, description="升版说明（替换项目时写入升级记录）")


class IpqcTemplateItemResponse(BaseModel):
    id: int
    test_item_id: int
    sort_order: int
    required: bool
    item_code: str | None = None
    item_name: str | None = None
    standard_value: str | None = None
    judge_type: str | None = None


class IpqcTemplateResponse(BaseModel):
    id: int
    template_code: str
    name: str
    process_id: str | None = None
    process_name: str | None = None
    version: int
    status: str
    remark: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[IpqcTemplateItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class IpqcTemplateListResponse(BaseModel):
    items: list[IpqcTemplateResponse]
    total: int
    page: int
    page_size: int


class IpqcTemplateVersionResponse(BaseModel):
    id: int
    template_id: int
    version: int
    change_note: str | None = None
    changed_by: str | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}


class IpqcTemplateVersionListResponse(BaseModel):
    items: list[IpqcTemplateVersionResponse]
    total: int


class IpqcItemResultIn(BaseModel):
    test_item_id: int | None = Field(None, description="测试项目 ID")
    item_code: str | None = Field(None, max_length=50, description="项目编码")
    item_name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    standard_value: str | None = Field(None, max_length=200, description="标准值")
    actual_value: str | None = Field(None, max_length=200, description="实测值")
    result: str = Field("pending", pattern="^(pass|fail|pending)$", description="项目结果")
    remark: str | None = Field(None, max_length=2000, description="备注")
    sort_order: int = Field(0, description="排序")


class IpqcRecordEntryCreate(BaseModel):
    """首件/巡检/复检/送检 录入（写入 quality_inspection_records）"""

    entry_type: str = Field(
        ...,
        pattern="^(first_article|patrol|reinspect|submit)$",
        description="录入类型：首件/巡检/复检/送检",
    )
    template_id: int | None = Field(None, description="本系统模板主键（优先）")
    template_code: str | None = Field(None, max_length=40, description="模板编码")
    process_id: str | None = Field(None, max_length=40, description="工序 ID")
    process_name: str | None = Field(None, max_length=50, description="工序名称")
    work_order_no: str | None = Field(None, max_length=50, description="工单号")
    batch_no: str | None = Field(None, max_length=50, description="批次号")
    scan_barcode: str | None = Field(None, max_length=100, description="条码")
    product_code: str | None = Field(None, max_length=50, description="产品/料号")
    material_code: str | None = Field(None, max_length=50, description="物料编码")
    customer_code: str | None = Field(None, max_length=50, description="客户代码")
    shift: str | None = Field(None, max_length=20, description="班次")
    inspected_qty: int | None = Field(None, ge=0, description="抽检数量")
    inspector: str | None = Field(None, max_length=50, description="检验人（空则取当前用户）")
    remark: str | None = Field(None, max_length=2000, description="备注")
    inspection_result: str | None = Field(
        None,
        pattern="^(pass|fail|pending)$",
        description="总结果；送检默认 pending，录入可传 pass/fail",
    )
    item_results: list[IpqcItemResultIn] = Field(
        default_factory=list, max_length=200, description="检验项目明细"
    )


class IpqcRecordUpdate(BaseModel):
    """IPQC 记录修改"""

    process_id: str | None = Field(None, max_length=40)
    process_name: str | None = Field(None, max_length=50)
    work_order_no: str | None = Field(None, max_length=50)
    batch_no: str | None = Field(None, max_length=50)
    scan_barcode: str | None = Field(None, max_length=100)
    product_code: str | None = Field(None, max_length=50)
    material_code: str | None = Field(None, max_length=50)
    customer_code: str | None = Field(None, max_length=50)
    shift: str | None = Field(None, max_length=20)
    inspected_qty: int | None = Field(None, ge=0)
    inspector: str | None = Field(None, max_length=50)
    remark: str | None = Field(None, max_length=2000)
    inspection_result: str | None = Field(None, pattern="^(pass|fail|pending)$")
    item_results: list[IpqcItemResultIn] | None = Field(
        None, max_length=200, description="若传入则整体替换明细"
    )


class IpqcItemResultResponse(BaseModel):
    id: int
    record_id: int
    test_item_id: int | None = None
    item_code: str | None = None
    item_name: str
    standard_value: str | None = None
    actual_value: str | None = None
    result: str
    remark: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class IpqcRecordDetailResponse(BaseModel):
    """检验记录详情（主表 + 明细）"""

    id: int
    inspection_no: str
    inspection_type: str
    inspection_result: str
    status: str
    ipqc_entry_type: str | None = None
    work_order_no: str | None = None
    product_code: str | None = None
    batch_no: str | None = None
    material_code: str | None = None
    inspector: str
    inspected_at: datetime
    inspected_qty: int | None = None
    non_conforming_qty: int
    remark: str | None = None
    template_id: str | None = None
    process_id: str | None = None
    process_name: str | None = None
    customer_code: str | None = None
    shift: str | None = None
    scan_barcode: str | None = None
    is_reinspection: int = 0
    item_results: list[IpqcItemResultResponse] = Field(default_factory=list)
    created_at: datetime
