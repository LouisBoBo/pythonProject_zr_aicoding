"""仓储看板 API — 从仓库 / 物料 / 库存 / 流水表查询。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    InventoryBalance,
    InventoryStock,
    InventoryTransaction,
    Material,
    MaterialInbound,
    User,
    Warehouse,
    WarehouseLocation,
)
from app.routers.sales_orders import SalesOrderListResponse, list_sales_orders
from app.schemas import (
    EmployeeWorkHourReportItem,
    EmployeeWorkHourReportListResponse,
    InventoryStockListResponse,
    InventoryStockResponse,
    MaterialInboundCreate,
    MaterialInboundListResponse,
    MaterialInboundResponse,
    MaterialOption,
    WarehouseActivityItem,
    WarehouseAlertItem,
    WarehouseDashboardResponse,
    WarehouseKpiCard,
    WarehouseLocationOption,
    WarehouseLocationSlice,
    WarehouseMaterialRow,
    WarehouseOption,
    WarehouseTrendBundle,
    WarehouseTrendSeries,
)
from app.routers.reports import (
    APPROVAL_STATUS_LABELS,
    WORK_HOUR_APPROVAL_VALUES,
    WORK_HOUR_DIMENSIONS,
    WORK_HOUR_SHIFT_VALUES,
    _build_work_hour_report_items,
    _normalize_work_hour_date_range,
)

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])

TXN_LABEL = {"in": "入库", "out": "出库", "move": "移库", "check": "盘点"}
LOCATION_LABEL = {"occupied": "已占用", "free": "空闲", "abnormal": "异常"}
LOCATION_COLOR = {"occupied": "#409eff", "free": "#67c23a", "abnormal": "#f56c6c"}


def _generate_inbound_no(db: Session) -> str:
    today = date.today()
    prefix = f"RK-{today:%Y%m%d}-"
    last = (
        db.query(MaterialInbound)
        .filter(MaterialInbound.inbound_no.like(f"{prefix}%"))
        .order_by(MaterialInbound.inbound_no.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.inbound_no.split("-")[-1]) + 1
        except ValueError:
            seq = db.query(MaterialInbound).count() + 1
    return f"{prefix}{seq:03d}"


def _apply_inbound_to_inventory(
    db: Session,
    inbound: MaterialInbound,
    *,
    txn_at: datetime | None = None,
) -> None:
    """已入库状态：更新库存余额、流水与汇总表。"""
    when = txn_at or datetime.combine(inbound.inbound_date, datetime.min.time()).replace(
        hour=10, minute=0, second=0
    )
    bal = (
        db.query(InventoryBalance)
        .filter(
            InventoryBalance.material_id == inbound.material_id,
            InventoryBalance.location_id == inbound.location_id,
        )
        .first()
    )
    if bal:
        bal.quantity += inbound.quantity
        bal.updated_at = when
    else:
        db.add(
            InventoryBalance(
                material_id=inbound.material_id,
                location_id=inbound.location_id,
                quantity=inbound.quantity,
                updated_at=when,
            )
        )

    db.add(
        InventoryTransaction(
            material_id=inbound.material_id,
            location_id=inbound.location_id,
            txn_type="in",
            quantity=inbound.quantity,
            txn_at=when,
            ref_no=inbound.inbound_no,
            remark=f"物料入库 {inbound.material_name}",
        )
    )

    stock = (
        db.query(InventoryStock)
        .filter(
            InventoryStock.material_id == inbound.material_id,
            InventoryStock.warehouse_id == inbound.warehouse_id,
        )
        .first()
    )
    if stock:
        stock.quantity += inbound.quantity
        stock.updated_at = when
    else:
        material = db.query(Material).filter(Material.id == inbound.material_id).first()
        if material:
            db.add(
                InventoryStock(
                    material_id=inbound.material_id,
                    material_code=inbound.material_code,
                    material_name=inbound.material_name,
                    warehouse_id=inbound.warehouse_id,
                    warehouse_name=inbound.warehouse_name,
                    quantity=inbound.quantity,
                    unit=inbound.unit,
                    safety_stock=material.safety_stock,
                    updated_at=when,
                )
            )

    if inbound.location_id:
        loc = db.query(WarehouseLocation).filter(WarehouseLocation.id == inbound.location_id).first()
        if loc and loc.status == "free":
            loc.status = "occupied"


def _trend_for(db: Session, txn_type: str) -> WarehouseTrendBundle:
    today = date.today()
    now = datetime.utcnow()

    # today hourly
    day_labels = [f"{h:02d}:00" for h in range(8, 18)]
    day_values = []
    for h in range(8, 18):
        start = datetime.combine(today, datetime.min.time()).replace(hour=h)
        end = start + timedelta(hours=1)
        qty = int(
            db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
            .filter(
                InventoryTransaction.txn_type == txn_type,
                InventoryTransaction.txn_at >= start,
                InventoryTransaction.txn_at < end,
            )
            .scalar()
            or 0
        )
        day_values.append(qty)

    # week daily
    week_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    # align to Monday of current week
    monday = today - timedelta(days=today.weekday())
    week_values = []
    for i in range(7):
        d = monday + timedelta(days=i)
        start = datetime.combine(d, datetime.min.time())
        end = start + timedelta(days=1)
        qty = int(
            db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
            .filter(
                InventoryTransaction.txn_type == txn_type,
                InventoryTransaction.txn_at >= start,
                InventoryTransaction.txn_at < end,
            )
            .scalar()
            or 0
        )
        week_values.append(qty)

    # month by week
    month_start = today.replace(day=1)
    month_labels = ["第1周", "第2周", "第3周", "第4周"]
    month_values = [0, 0, 0, 0]
    rows = (
        db.query(InventoryTransaction)
        .filter(
            InventoryTransaction.txn_type == txn_type,
            InventoryTransaction.txn_at >= datetime.combine(month_start, datetime.min.time()),
            InventoryTransaction.txn_at <= now,
        )
        .all()
    )
    for r in rows:
        week_idx = min(3, (r.txn_at.date() - month_start).days // 7)
        month_values[week_idx] += r.quantity

    return WarehouseTrendBundle(
        today=WarehouseTrendSeries(
            labels=day_labels, values=day_values, summary=sum(day_values)
        ),
        week=WarehouseTrendSeries(
            labels=week_labels, values=week_values, summary=sum(week_values)
        ),
        month=WarehouseTrendSeries(
            labels=month_labels, values=month_values, summary=sum(month_values)
        ),
    )


@router.get("/dashboard", response_model=WarehouseDashboardResponse)
def warehouse_dashboard(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_stock = int(
        db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0)).scalar() or 0
    )
    sku_count = db.query(Material).count()
    loc_rows = (
        db.query(WarehouseLocation.status, func.count(WarehouseLocation.id))
        .group_by(WarehouseLocation.status)
        .all()
    )
    loc_map = {s: c for s, c in loc_rows}
    occupied = loc_map.get("occupied", 0)
    free = loc_map.get("free", 0)
    abnormal = loc_map.get("abnormal", 0)
    loc_total = occupied + free + abnormal or 1
    usage = round(occupied / loc_total * 100, 1)

    # turnover approx: month outbound / avg stock
    month_start = date.today().replace(day=1)
    month_out = int(
        db.query(func.coalesce(func.sum(InventoryTransaction.quantity), 0))
        .filter(
            InventoryTransaction.txn_type == "out",
            InventoryTransaction.txn_at
            >= datetime.combine(month_start, datetime.min.time()),
        )
        .scalar()
        or 0
    )
    turnover = round(month_out / max(total_stock, 1) * 30, 1)

    kpi_cards = [
        WarehouseKpiCard(
            key="total_stock",
            label="总库存量",
            value=f"{total_stock:,}",
            unit="件",
            sub="",
            color="#409eff",
        ),
        WarehouseKpiCard(
            key="sku_count",
            label="SKU 数",
            value=f"{sku_count:,}",
            unit="个",
            sub="",
            color="#67c23a",
        ),
        WarehouseKpiCard(
            key="location_usage",
            label="库位使用率",
            value=str(usage),
            unit="%",
            sub=f"空闲 {round(free / loc_total * 100, 1)}%",
            color="#e6a23c",
        ),
        WarehouseKpiCard(
            key="turnover",
            label="周转率",
            value=str(turnover),
            unit="次/月",
            sub="",
            color="#f56c6c",
        ),
    ]

    alerts = []
    materials = db.query(Material).order_by(Material.id).all()
    for m in materials:
        qty = int(
            db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0))
            .filter(InventoryBalance.material_id == m.id)
            .scalar()
            or 0
        )
        if qty < m.safety_stock:
            alerts.append(
                WarehouseAlertItem(
                    level="danger",
                    text=f"物料「{m.material_name}」库存低于安全库存（当前 {qty}，安全 {m.safety_stock}）",
                )
            )
        elif qty == 0:
            alerts.append(
                WarehouseAlertItem(
                    level="warning",
                    text=f"物料「{m.material_name}」库存为 0，请及时补货",
                )
            )
        elif qty < m.safety_stock * 1.1:
            alerts.append(
                WarehouseAlertItem(
                    level="warning",
                    text=f"物料「{m.material_name}」接近安全库存（当前 {qty}，安全 {m.safety_stock}）",
                )
            )

    location_distribution = [
        WarehouseLocationSlice(
            name=LOCATION_LABEL.get(status, status),
            value=count,
            color=LOCATION_COLOR.get(status, "#909399"),
        )
        for status, count in (("occupied", occupied), ("free", free), ("abnormal", abnormal))
        if count or status == "occupied"
    ]

    txns = (
        db.query(InventoryTransaction)
        .options(joinedload(InventoryTransaction.material))
        .order_by(InventoryTransaction.txn_at.desc())
        .limit(20)
        .all()
    )
    activities = []
    for t in txns:
        loc = (
            db.query(WarehouseLocation).filter(WarehouseLocation.id == t.location_id).first()
            if t.location_id
            else None
        )
        loc_code = loc.location_code if loc else "-"
        name = t.material.material_name if t.material else "-"
        arrow = "→" if t.txn_type == "in" else "←" if t.txn_type == "out" else ""
        if t.txn_type == "move":
            text = t.remark or f"物料「{name}」移库 {t.quantity} 件"
        elif t.txn_type == "check":
            text = t.remark or f"库位 {loc_code} 盘点完成"
        else:
            text = f"物料「{name}」{TXN_LABEL.get(t.txn_type, t.txn_type)} {t.quantity} 件 {arrow} {loc_code}"
        activities.append(
            WarehouseActivityItem(
                time=t.txn_at.strftime("%H:%M:%S"),
                type=t.txn_type,
                typeLabel=TXN_LABEL.get(t.txn_type, t.txn_type),
                text=text,
            )
        )

    material_rows = []
    categories = set()
    for m in materials:
        bal = (
            db.query(InventoryBalance)
            .options(joinedload(InventoryBalance.location))
            .filter(InventoryBalance.material_id == m.id)
            .first()
        )
        qty = int(
            db.query(func.coalesce(func.sum(InventoryBalance.quantity), 0))
            .filter(InventoryBalance.material_id == m.id)
            .scalar()
            or 0
        )
        loc_code = bal.location.location_code if bal and bal.location else None
        updated = bal.updated_at.strftime("%Y-%m-%d %H:%M") if bal else ""
        categories.add(m.category)
        material_rows.append(
            WarehouseMaterialRow(
                material_code=m.material_code,
                material_name=m.material_name,
                category=m.category,
                spec=m.spec,
                unit=m.unit,
                stock_qty=qty,
                safety_stock=m.safety_stock,
                location_code=loc_code,
                last_update=updated,
            )
        )

    return WarehouseDashboardResponse(
        kpi_cards=kpi_cards,
        inbound=_trend_for(db, "in"),
        outbound=_trend_for(db, "out"),
        alerts=alerts[:10],
        location_distribution=location_distribution,
        activities=activities,
        materials=material_rows,
        categories=sorted(categories),
    )


@router.get("/inventory-stock", response_model=InventoryStockListResponse)
def list_inventory_stock(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    material_code: str | None = Query(None, description="物料编码（模糊）"),
    material_name: str | None = Query(None, description="物料名称（模糊）"),
    warehouse_name: str | None = Query(None, description="仓库名称（模糊）"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """物料库存列表：支持按物料编码、名称、仓库筛选，后端分页。"""
    query = db.query(InventoryStock)
    if material_code:
        query = query.filter(InventoryStock.material_code.ilike(f"%{material_code}%"))
    if material_name:
        query = query.filter(InventoryStock.material_name.ilike(f"%{material_name}%"))
    if warehouse_name:
        query = query.filter(InventoryStock.warehouse_name.ilike(f"%{warehouse_name}%"))

    total = query.count()
    quantity_sum = int(
        query.with_entities(func.coalesce(func.sum(InventoryStock.quantity), 0)).scalar() or 0
    )
    rows = (
        query.order_by(InventoryStock.material_code.asc(), InventoryStock.warehouse_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return InventoryStockListResponse(
        items=[InventoryStockResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        quantity_sum=quantity_sum,
    )


@router.get("/warehouses", response_model=list[WarehouseOption])
def list_warehouses(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仓库下拉选项（用于库存筛选）。"""
    return db.query(Warehouse).order_by(Warehouse.code).all()


@router.get("/materials", response_model=list[MaterialOption])
def list_materials(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """物料下拉选项（用于入库表单）。"""
    return db.query(Material).order_by(Material.material_code).all()


@router.get("/locations", response_model=list[WarehouseLocationOption])
def list_locations(
    warehouse_id: int | None = Query(None, description="按仓库筛选库位"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """库位下拉选项（用于入库表单）。"""
    query = (
        db.query(WarehouseLocation, Warehouse)
        .join(Warehouse, WarehouseLocation.warehouse_id == Warehouse.id)
        .order_by(WarehouseLocation.location_code)
    )
    if warehouse_id:
        query = query.filter(WarehouseLocation.warehouse_id == warehouse_id)
    rows = query.all()
    return [
        WarehouseLocationOption(
            id=loc.id,
            location_code=loc.location_code,
            warehouse_id=wh.id,
            warehouse_name=wh.name,
            status=loc.status,
        )
        for loc, wh in rows
    ]


@router.get("/material-inbound", response_model=MaterialInboundListResponse)
def list_material_inbound(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    inbound_no: str | None = Query(None, description="入库单号（模糊）"),
    material_code: str | None = Query(None, description="物料编码（模糊）"),
    material_name: str | None = Query(None, description="物料名称（模糊）"),
    status: str | None = Query(None, description="状态：pending/completed"),
    date_from: date | None = Query(None, description="入库日期起"),
    date_to: date | None = Query(None, description="入库日期止"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """物料入库列表：支持按单号、物料、状态、入库日期范围筛选，后端分页。"""
    query = db.query(MaterialInbound)
    if inbound_no:
        query = query.filter(MaterialInbound.inbound_no.ilike(f"%{inbound_no}%"))
    if material_code:
        query = query.filter(MaterialInbound.material_code.ilike(f"%{material_code}%"))
    if material_name:
        query = query.filter(MaterialInbound.material_name.ilike(f"%{material_name}%"))
    if status:
        query = query.filter(MaterialInbound.status == status)
    if date_from:
        query = query.filter(MaterialInbound.inbound_date >= date_from)
    if date_to:
        query = query.filter(MaterialInbound.inbound_date <= date_to)

    total = query.count()
    rows = (
        query.order_by(MaterialInbound.inbound_date.desc(), MaterialInbound.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialInboundListResponse(
        items=[MaterialInboundResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/material-inbound", response_model=MaterialInboundResponse, status_code=201)
def create_material_inbound(
    payload: MaterialInboundCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增物料入库：落库 material_inbounds；状态为已入库时同步更新库存。"""
    if payload.status not in ("pending", "completed"):
        raise HTTPException(status_code=400, detail="状态仅支持 pending（待入库）或 completed（已入库）")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="入库数量须大于 0")

    material = db.query(Material).filter(Material.id == payload.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")

    warehouse = db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")

    location_code = None
    if payload.location_id:
        loc = (
            db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == payload.location_id,
                WarehouseLocation.warehouse_id == payload.warehouse_id,
            )
            .first()
        )
        if not loc:
            raise HTTPException(status_code=400, detail="库位不存在或不属于所选仓库")
        location_code = loc.location_code

    inbound = MaterialInbound(
        inbound_no=_generate_inbound_no(db),
        material_id=material.id,
        material_code=material.material_code,
        material_name=material.material_name,
        spec=material.spec,
        quantity=payload.quantity,
        unit=material.unit,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        location_id=payload.location_id,
        location_code=location_code,
        inbound_date=payload.inbound_date,
        handler=payload.handler or current_user.username,
        status=payload.status,
    )
    db.add(inbound)
    try:
        db.flush()
        if payload.status == "completed":
            _apply_inbound_to_inventory(db, inbound)
        db.commit()
        db.refresh(inbound)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="入库单号冲突，请重试")

    return MaterialInboundResponse.model_validate(inbound)


@router.get(
    "/sales-orders",
    response_model=SalesOrderListResponse,
    summary="销售订单列表",
)
def warehouse_list_sales_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None, description="订单号或客户（模糊）"),
    status: str | None = Query(None, description="状态 open / closed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """销售订单列表（含下单时间 order_time），与 /api/sales-orders 字段一致。"""
    return list_sales_orders(
        page=page,
        size=size,
        keyword=keyword,
        status=status,
        _current_user=current_user,
        db=db,
    )


LISI_E1002_SEPT27_WORK_DATE = date(2026, 9, 27)
LISI_E1002_SEPT27_NIGHT_OVERTIME_HOURS = 2.0
LISI_E1002_SEPT27_INSERT_INDEX = 1

WORK_HOUR_STATUS_FILTER_VALUES = frozenset({"pending_effect", "effective", "void"})
WORK_HOUR_STATUS_BY_APPROVAL_LABEL = {
    "待审批": "待生效",
    "已通过": "已生效",
    "已驳回": "已作废",
}
WORK_HOUR_STATUS_FILTER_LABELS = {
    "pending_effect": "待生效",
    "effective": "已生效",
    "void": "已作废",
}


def _enrich_work_hour_report_rows(
    items: list[EmployeeWorkHourReportItem],
) -> list[EmployeeWorkHourReportItem]:
    enriched: list[EmployeeWorkHourReportItem] = []
    for item in items:
        approval = item.approval_status or "—"
        if approval == "汇总":
            status = "汇总"
        else:
            status = WORK_HOUR_STATUS_BY_APPROVAL_LABEL.get(approval, "—")
        enriched.append(item.model_copy(update={"status": status}))
    return enriched


def _filter_work_hour_rows_by_approval(
    items: list[EmployeeWorkHourReportItem],
    approval_status: str | None,
) -> list[EmployeeWorkHourReportItem]:
    if not approval_status:
        return items
    label = APPROVAL_STATUS_LABELS.get(approval_status, approval_status)
    return [item for item in items if (item.approval_status or "—") == label]


def _filter_work_hour_rows_by_status(
    items: list[EmployeeWorkHourReportItem],
    status: str | None,
) -> list[EmployeeWorkHourReportItem]:
    if not status:
        return items
    label = WORK_HOUR_STATUS_FILTER_LABELS.get(status, status)
    return [item for item in items if (item.status or "—") == label]


def _lisi_sept27_night_overtime_row() -> EmployeeWorkHourReportItem:
    """李四（E1002）9 月 27 日晚班加班 2 小时（员工工时报表标注行）。"""
    return EmployeeWorkHourReportItem(
        employee_name="李四",
        employee_no="E1002",
        department="生产一部",
        project_name="PCB-B 试产项目",
        task_name="焊接调试",
        work_date=LISI_E1002_SEPT27_WORK_DATE,
        shift_type="晚班",
        work_hours=8.0,
        overtime_hours=LISI_E1002_SEPT27_NIGHT_OVERTIME_HOURS,
        approval_status="待审批",
    )


def _insert_lisi_e1002_sept27_night_overtime(
    items: list[EmployeeWorkHourReportItem],
    *,
    dimension: str,
    date_from: date,
    date_to: date,
    department: str | None = None,
    employee_no: str | None = None,
    project_name: str | None = None,
    shift_type: str | None = None,
) -> list[EmployeeWorkHourReportItem]:
    """员工工时报表：新增李四 9/27 晚班加班 2h；列表插入位置见 LISI_E1002_SEPT27_INSERT_INDEX。"""
    if dimension != "detail":
        return items
    if date_from > LISI_E1002_SEPT27_WORK_DATE or date_to < LISI_E1002_SEPT27_WORK_DATE:
        return items
    if shift_type == "day":
        return items
    if department and department != "生产一部":
        return items
    if employee_no and employee_no != "E1002":
        return items
    if project_name and project_name != "PCB-B 试产项目":
        return items

    new_row = _lisi_sept27_night_overtime_row()
    for item in items:
        if (
            item.employee_name == new_row.employee_name
            and item.employee_no == new_row.employee_no
            and item.work_date == new_row.work_date
            and item.shift_type == new_row.shift_type
            and item.overtime_hours == new_row.overtime_hours
        ):
            return items

    result = list(items)
    insert_at = len(result)
    for i, item in enumerate(items):
        if (
            item.employee_name == "李四"
            and item.employee_no == "E1002"
            and item.department == "生产一部"
        ):
            insert_at = i + 1
            break
    else:
        insert_at = min(LISI_E1002_SEPT27_INSERT_INDEX, len(result))
    result.insert(insert_at, new_row)
    return result


@router.get(
    "/employee-work-hours",
    response_model=EmployeeWorkHourReportListResponse,
    summary="员工工时报表列表",
    description="员工工时报表页列表数据；含李四（E1002）9月27日晚班加班2小时。",
)
def warehouse_list_employee_work_hours(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    date_from: date | None = Query(None, description="日期起（含）"),
    date_to: date | None = Query(None, description="日期止（含）"),
    department: str | None = Query(None, description="部门筛选"),
    employee_no: str | None = Query(None, description="工号筛选"),
    project_name: str | None = Query(None, description="项目筛选"),
    shift_type: str | None = Query(
        None,
        description="班别筛选：不传或空=全部；day=白班；night=晚班",
    ),
    approval_status: str | None = Query(
        None,
        description="审批筛选：pending=待审批；approved=已通过；rejected=已驳回",
    ),
    status: str | None = Query(
        None,
        description="状态筛选：pending_effect=待生效；effective=已生效；void=已作废",
    ),
    dimension: str = Query("detail", description="统计维度，明细=detail"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if dimension not in WORK_HOUR_DIMENSIONS:
        dimension = "detail"
    if shift_type == "":
        shift_type = None
    if shift_type is not None and shift_type not in WORK_HOUR_SHIFT_VALUES:
        raise HTTPException(status_code=400, detail="班别无效，应为 day 或 night")
    if approval_status == "":
        approval_status = None
    if approval_status is not None and approval_status not in WORK_HOUR_APPROVAL_VALUES:
        raise HTTPException(status_code=400, detail="审批无效，应为 pending、approved 或 rejected")
    if status == "":
        status = None
    if status is not None and status not in WORK_HOUR_STATUS_FILTER_VALUES:
        raise HTTPException(
            status_code=400,
            detail="状态无效，应为 pending_effect、effective 或 void",
        )
    date_from, date_to = _normalize_work_hour_date_range(date_from, date_to)

    all_items = _build_work_hour_report_items(
        db,
        date_from=date_from,
        date_to=date_to,
        department=department,
        employee_no=employee_no,
        project_name=project_name,
        shift_type=shift_type,
        dimension=dimension,
    )
    all_items = _insert_lisi_e1002_sept27_night_overtime(
        all_items,
        dimension=dimension,
        date_from=date_from,
        date_to=date_to,
        department=department,
        employee_no=employee_no,
        project_name=project_name,
        shift_type=shift_type,
    )
    all_items = _enrich_work_hour_report_rows(all_items)
    all_items = _filter_work_hour_rows_by_approval(all_items, approval_status)
    all_items = _filter_work_hour_rows_by_status(all_items, status)
    total = len(all_items)
    work_hours_sum = round(sum(i.work_hours for i in all_items), 2)
    overtime_hours_sum = round(sum(i.overtime_hours for i in all_items), 2)
    start = (page - 1) * page_size
    page_items = all_items[start : start + page_size]

    return EmployeeWorkHourReportListResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        dimension=dimension,
        work_hours_sum=work_hours_sum,
        overtime_hours_sum=overtime_hours_sum,
    )
