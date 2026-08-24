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
from app.schemas import (
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
