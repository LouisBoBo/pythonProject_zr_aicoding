"""品质检验记录 / 检验任务 API Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class QualityInspectionRecordResponse(BaseModel):
    """检验记录列表行"""

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
    created_at: datetime

    model_config = {"from_attributes": True}


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
