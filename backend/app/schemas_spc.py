"""SPC 控制图接口模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SpcChartListItem(BaseModel):
    id: int
    chart_code: str = Field(description="控制图编码")
    chart_name: str = Field(description="控制图名称")
    process_name: str = Field(description="工序")
    characteristic: str = Field(description="质量特性")
    chart_type: str = Field(description="图类型 I-MR / Xbar-R")
    subgroup_size: int = Field(description="子组大小")
    unit: str | None = None
    usl: float | None = Field(None, description="上规格限")
    lsl: float | None = Field(None, description="下规格限")
    target: float | None = None
    ucl: float | None = Field(None, description="上控制限")
    cl: float | None = Field(None, description="中心线")
    lcl: float | None = Field(None, description="下控制限")
    cp: float | None = None
    cpk: float | None = None
    status: str = Field(description="normal / alert")
    sample_count: int = Field(0, description="测量点数")
    updated_at: datetime | None = None


class SpcChartListResponse(BaseModel):
    items: list[SpcChartListItem]
    total: int


class SpcPointItem(BaseModel):
    index: int
    value: float
    out_of_control: bool = False
    range: float | None = None
    measured_at: str | None = None
    sample_label: str | None = None


class SpcChartDetailResponse(BaseModel):
    id: int
    chart_code: str
    chart_name: str
    process_name: str
    characteristic: str
    chart_type: str
    subgroup_size: int
    unit: str | None = None
    usl: float | None = None
    lsl: float | None = None
    target: float | None = None
    ucl: float | None = None
    cl: float | None = None
    lcl: float | None = None
    cp: float | None = None
    cpk: float | None = None
    status: str
    sample_count: int
    points: list[SpcPointItem]
    out_of_control_indexes: list[int] = Field(default_factory=list)
    updated_at: datetime | None = None


class SpcComputeRequest(BaseModel):
    values: list[float] = Field(
        ..., min_length=1, max_length=5000, description="测量值序列（最多 5000 点）"
    )
    chart_type: str = Field("I-MR", description="I-MR 或 Xbar-R")
    subgroup_size: int = Field(1, ge=1, le=10, description="子组大小（Xbar-R 时生效）")
    usl: float | None = Field(None, description="上规格限")
    lsl: float | None = Field(None, description="下规格限")


class SpcComputeResponse(BaseModel):
    chart_type: str
    sample_count: int
    ucl: float | None = None
    cl: float | None = None
    lcl: float | None = None
    cp: float | None = None
    cpk: float | None = None
    status: str
    points: list[SpcPointItem]
    out_of_control_indexes: list[int] = Field(default_factory=list)


class SpcFiltersResponse(BaseModel):
    process_names: list[str] = Field(description="工序选项")
    characteristics: list[str] = Field(description="特性选项")
    chart_types: list[str] = Field(description="图类型选项")
