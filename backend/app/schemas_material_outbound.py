"""生产领料出库 Pydantic 模型。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class MaterialOutboundResponse(BaseModel):
    id: int
    outbound_no: str
    outbound_type: str
    material_id: int
    material_code: str
    material_name: str
    spec: str | None = None
    batch_no: str | None = None
    quantity: int
    unit: str
    warehouse_id: int
    warehouse_name: str
    location_id: int | None = None
    location_code: str | None = None
    outbound_date: date
    picker: str | None = None
    receiver_department: str | None = None
    remark: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialOutboundListResponse(BaseModel):
    items: list[MaterialOutboundResponse]
    total: int
    page: int
    page_size: int


class MaterialOutboundCreate(BaseModel):
    material_id: int
    quantity: int = Field(gt=0, description="出库数量须大于 0")
    warehouse_id: int
    location_id: int | None = None
    batch_no: str | None = None
    outbound_date: date
    picker: str | None = None
    receiver_department: str | None = None
    remark: str | None = None
    status: str = "completed"


class MaterialOutboundStockBalanceResponse(BaseModel):
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    available_quantity: int
    unit: str | None = None
