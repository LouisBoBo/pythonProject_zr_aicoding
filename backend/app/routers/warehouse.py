"""仓储看板 API — 从仓库 / 物料 / 库存 / 流水表查询。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    InventoryBalance,
    InventoryTransaction,
    Material,
    User,
    WarehouseLocation,
)
from app.schemas import (
    WarehouseActivityItem,
    WarehouseAlertItem,
    WarehouseDashboardResponse,
    WarehouseKpiCard,
    WarehouseLocationSlice,
    WarehouseMaterialRow,
    WarehouseTrendBundle,
    WarehouseTrendSeries,
)

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])

TXN_LABEL = {"in": "入库", "out": "出库", "move": "移库", "check": "盘点"}
LOCATION_LABEL = {"occupied": "已占用", "free": "空闲", "abnormal": "异常"}
LOCATION_COLOR = {"occupied": "#409eff", "free": "#67c23a", "abnormal": "#f56c6c"}


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
