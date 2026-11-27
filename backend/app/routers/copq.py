"""客诉台账与 COPQ 金额接口。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.copq_store import Customer, CustomerComplaint, ensure_copq_schema
from app.database import engine, get_db
from app.models import User
from app.permissions import QUALITY_WRITE, require_permissions
from app.schemas_copq import (
    ComplaintCreateRequest,
    ComplaintItem,
    ComplaintListResponse,
    CopqByCategoryItem,
    CopqByCustomerItem,
    CopqSummaryResponse,
    CopqTrendItem,
    CustomerItem,
    CustomerListResponse,
)

router = APIRouter(prefix="/api/quality", tags=["客诉与COPQ"])

ALLOWED_COST_CATEGORIES = frozenset({"scrap", "rework", "return", "claim"})
ALLOWED_COMPLAINT_TYPES = frozenset({"质量", "交期", "服务"})

ensure_copq_schema(engine)


def _to_complaint_item(row: CustomerComplaint) -> ComplaintItem:
    return ComplaintItem(
        id=row.id,
        complaint_no=row.complaint_no,
        customer_code=row.customer_code,
        customer_name=row.customer_name,
        complaint_date=row.complaint_date,
        complaint_type=row.complaint_type,
        severity=row.severity,
        product_code=row.product_code,
        product_name=row.product_name,
        affected_qty=row.affected_qty,
        cost_category=row.cost_category,
        unit_cost=float(row.unit_cost or 0),
        copq_amount=float(row.copq_amount or 0),
        currency=row.currency,
        problem_description=row.problem_description,
        status=row.status,
        assigned_to=row.assigned_to,
        closed_date=row.closed_date,
        created_at=row.created_at,
    )


@router.get(
    "/customers",
    response_model=CustomerListResponse,
    summary="客户主数据列表",
    description="查询 ERP 客户主数据（客诉/COPQ 依赖的客户字段）；支持编码或名称模糊搜索。",
)
def list_customers(
    keyword: str | None = Query(None, description="客户编码或名称（模糊）"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Customer)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (Customer.customer_code.ilike(like)) | (Customer.customer_name.ilike(like))
        )
    rows = q.order_by(Customer.customer_code.asc()).all()
    items = [
        CustomerItem(
            id=r.id,
            customer_code=r.customer_code,
            customer_name=r.customer_name,
            contact_person=r.contact_person,
            contact_phone=r.contact_phone,
            region=r.region,
            status=r.status,
        )
        for r in rows
    ]
    return CustomerListResponse(items=items, total=len(items))


@router.get(
    "/complaints",
    response_model=ComplaintListResponse,
    summary="客诉台账列表",
    description="分页查询客户投诉记录，含 COPQ 金额与成本类别；客诉/COPQ 分析页数据来自本接口。",
)
def list_complaints(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    customer_code: str | None = Query(None, description="客户编码"),
    status: str | None = Query(None, description="状态 open/processing/closed"),
    date_from: date | None = Query(None, description="投诉日起"),
    date_to: date | None = Query(None, description="投诉日止"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(CustomerComplaint)
    if customer_code:
        q = q.filter(CustomerComplaint.customer_code == customer_code)
    if status:
        q = q.filter(CustomerComplaint.status == status)
    if date_from:
        q = q.filter(CustomerComplaint.complaint_date >= date_from)
    if date_to:
        q = q.filter(CustomerComplaint.complaint_date <= date_to)

    total = q.count()
    rows = (
        q.order_by(CustomerComplaint.complaint_date.desc(), CustomerComplaint.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ComplaintListResponse(
        items=[_to_complaint_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/complaints",
    response_model=ComplaintItem,
    summary="新建客诉记录",
    description=(
        "录入客诉并自动按客户主数据补齐客户名称；"
        "COPQ 金额一律由服务端按 影响数量×单位成本 计算（忽略客户端传入金额）；"
        "需 quality.write 权限。"
    ),
)
def create_complaint(
    body: ComplaintCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    _ = current_user
    code = (body.customer_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="客户编码不能为空")
    if body.cost_category not in ALLOWED_COST_CATEGORIES:
        raise HTTPException(status_code=400, detail="成本类别无效")
    if body.complaint_type not in ALLOWED_COMPLAINT_TYPES:
        raise HTTPException(status_code=400, detail="投诉类型无效")

    cust = db.query(Customer).filter(Customer.customer_code == code).first()
    if not cust:
        raise HTTPException(status_code=400, detail=f"客户编码不存在：{code}")

    # 金额仅服务端计算，防止任意篡改 COPQ 报表
    amount = round(float(body.affected_qty) * float(body.unit_cost), 2)

    today = date.today()
    seq = db.query(CustomerComplaint).count() + 1
    complaint_no = f"CC{today.strftime('%Y%m%d')}{seq:04d}"
    while db.query(CustomerComplaint).filter(CustomerComplaint.complaint_no == complaint_no).first():
        seq += 1
        complaint_no = f"CC{today.strftime('%Y%m%d')}{seq:04d}"

    row = CustomerComplaint(
        complaint_no=complaint_no,
        customer_id=cust.id,
        customer_code=cust.customer_code,
        customer_name=cust.customer_name,
        complaint_date=body.complaint_date or today,
        complaint_type=body.complaint_type,
        severity=body.severity,
        product_code=body.product_code,
        product_name=body.product_name,
        affected_qty=body.affected_qty,
        cost_category=body.cost_category,
        unit_cost=body.unit_cost,
        copq_amount=amount,
        problem_description=body.problem_description,
        status="open",
        assigned_to=body.assigned_to,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_complaint_item(row)


@router.get(
    "/copq-summary",
    response_model=CopqSummaryResponse,
    summary="COPQ 金额汇总",
    description=(
        "按期间汇总客诉 COPQ 金额：总金额、未关闭件数、按客户/成本类别分布与按日趋势。"
        "成本字段来自客诉台账的 unit_cost / copq_amount。"
    ),
)
def copq_summary(
    date_from: date | None = Query(None, description="起始日期，默认近 30 天"),
    date_to: date | None = Query(None, description="结束日期，默认今天"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=29)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    base = db.query(CustomerComplaint).filter(
        CustomerComplaint.complaint_date >= date_from,
        CustomerComplaint.complaint_date <= date_to,
    )
    total_complaints = base.count()
    total_amount = float(
        db.query(func.coalesce(func.sum(CustomerComplaint.copq_amount), 0))
        .filter(
            CustomerComplaint.complaint_date >= date_from,
            CustomerComplaint.complaint_date <= date_to,
        )
        .scalar()
        or 0
    )
    open_count = base.filter(CustomerComplaint.status != "closed").count()

    by_cust_rows = (
        db.query(
            CustomerComplaint.customer_code,
            CustomerComplaint.customer_name,
            func.count(CustomerComplaint.id),
            func.coalesce(func.sum(CustomerComplaint.copq_amount), 0),
        )
        .filter(
            CustomerComplaint.complaint_date >= date_from,
            CustomerComplaint.complaint_date <= date_to,
        )
        .group_by(CustomerComplaint.customer_code, CustomerComplaint.customer_name)
        .order_by(func.sum(CustomerComplaint.copq_amount).desc())
        .all()
    )
    by_customer = [
        CopqByCustomerItem(
            customer_code=r[0],
            customer_name=r[1],
            complaint_count=int(r[2]),
            copq_amount=round(float(r[3]), 2),
        )
        for r in by_cust_rows
    ]

    by_cat_rows = (
        db.query(
            CustomerComplaint.cost_category,
            func.count(CustomerComplaint.id),
            func.coalesce(func.sum(CustomerComplaint.copq_amount), 0),
        )
        .filter(
            CustomerComplaint.complaint_date >= date_from,
            CustomerComplaint.complaint_date <= date_to,
        )
        .group_by(CustomerComplaint.cost_category)
        .order_by(func.sum(CustomerComplaint.copq_amount).desc())
        .all()
    )
    by_category = [
        CopqByCategoryItem(
            cost_category=r[0],
            complaint_count=int(r[1]),
            copq_amount=round(float(r[2]), 2),
        )
        for r in by_cat_rows
    ]

    daily_rows = (
        db.query(
            CustomerComplaint.complaint_date,
            func.count(CustomerComplaint.id),
            func.coalesce(func.sum(CustomerComplaint.copq_amount), 0),
        )
        .filter(
            CustomerComplaint.complaint_date >= date_from,
            CustomerComplaint.complaint_date <= date_to,
        )
        .group_by(CustomerComplaint.complaint_date)
        .order_by(CustomerComplaint.complaint_date.asc())
        .all()
    )
    daily_trend = [
        CopqTrendItem(
            date=r[0],
            complaint_count=int(r[1]),
            copq_amount=round(float(r[2]), 2),
        )
        for r in daily_rows
    ]

    return CopqSummaryResponse(
        date_from=date_from,
        date_to=date_to,
        total_complaints=total_complaints,
        total_copq_amount=round(total_amount, 2),
        open_count=open_count,
        by_customer=by_customer,
        by_category=by_category,
        daily_trend=daily_trend,
    )
