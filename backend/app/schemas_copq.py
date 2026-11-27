"""客诉 / COPQ 接口模型。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CustomerItem(BaseModel):
    id: int
    customer_code: str = Field(description="客户编码")
    customer_name: str = Field(description="客户名称")
    contact_person: str | None = Field(None, description="联系人")
    contact_phone: str | None = Field(None, description="联系电话")
    region: str | None = Field(None, description="区域")
    status: str = Field(description="状态 active/inactive")


class CustomerListResponse(BaseModel):
    items: list[CustomerItem]
    total: int


class ComplaintCreateRequest(BaseModel):
    customer_code: str = Field(..., description="客户编码")
    complaint_date: date | None = Field(None, description="投诉日期，默认今天")
    complaint_type: str = Field("质量", description="投诉类型：质量/交期/服务")
    severity: int = Field(3, ge=1, le=5, description="严重度 1-5")
    product_code: str | None = Field(None, description="产品编码")
    product_name: str | None = Field(None, description="产品名称")
    affected_qty: int = Field(0, ge=0, description="影响数量")
    cost_category: str = Field(
        "claim", description="成本类别：scrap/rework/return/claim"
    )
    unit_cost: float = Field(0, ge=0, description="单位成本（元）")
    problem_description: str | None = Field(None, description="问题描述")
    assigned_to: str | None = Field(None, description="责任人")


class ComplaintItem(BaseModel):
    id: int
    complaint_no: str = Field(description="客诉单号")
    customer_code: str = Field(description="客户编码")
    customer_name: str = Field(description="客户名称")
    complaint_date: date = Field(description="投诉日期")
    complaint_type: str = Field(description="投诉类型")
    severity: int = Field(description="严重度")
    product_code: str | None = None
    product_name: str | None = None
    affected_qty: int = Field(description="影响数量")
    cost_category: str = Field(description="成本类别")
    unit_cost: float = Field(description="单位成本")
    copq_amount: float = Field(description="COPQ 金额（元）")
    currency: str = "CNY"
    problem_description: str | None = None
    status: str = Field(description="状态 open/processing/closed")
    assigned_to: str | None = None
    closed_date: date | None = None
    created_at: datetime


class ComplaintListResponse(BaseModel):
    items: list[ComplaintItem]
    total: int
    page: int
    page_size: int


class CopqByCustomerItem(BaseModel):
    customer_code: str
    customer_name: str
    complaint_count: int = Field(description="客诉件数")
    copq_amount: float = Field(description="COPQ 合计（元）")


class CopqByCategoryItem(BaseModel):
    cost_category: str = Field(description="成本类别")
    complaint_count: int
    copq_amount: float


class CopqTrendItem(BaseModel):
    date: date
    complaint_count: int
    copq_amount: float


class CopqSummaryResponse(BaseModel):
    date_from: date
    date_to: date
    total_complaints: int = Field(description="客诉件数")
    total_copq_amount: float = Field(description="COPQ 合计金额（元）")
    open_count: int = Field(description="未关闭件数")
    by_customer: list[CopqByCustomerItem] = Field(description="按客户汇总")
    by_category: list[CopqByCategoryItem] = Field(description="按成本类别汇总")
    daily_trend: list[CopqTrendItem] = Field(description="按日趋势")
