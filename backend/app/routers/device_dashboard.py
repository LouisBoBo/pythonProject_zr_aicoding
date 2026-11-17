"""设备看板 API（/api/device/*）。

与 openapi_zh、frontend deviceDashboard.js、WorkBuddy mes_analyzer 对齐。
数据来自 equipment OEE 快照、运行日志、告警与产量记录；OEE 汇总逻辑复用报表模块。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Equipment,
    EquipmentAlarm,
    EquipmentOutputRecord,
    EquipmentRuntimeLog,
    User,
)
from app.routers.reports import (
    _build_equipment_oee_report_items,
    _build_equipment_oee_summary,
    _build_equipment_oee_trend,
    _normalize_equipment_oee_date_range,
)

router = APIRouter(prefix="/api/device", tags=["设备看板"])

_STATUS_BUCKETS = ("运行", "停机", "待机", "维修")


@router.get(
    "/status/summary",
    summary="设备状态汇总",
    description="按运行/停机/待机/维修统计设备台数与占比。",
)
def device_status_summary(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Equipment.status, func.count(Equipment.id)).group_by(Equipment.status).all()
    counts = {str(s or "未知"): int(c) for s, c in rows}
    total = sum(counts.values()) or 1
    items = []
    for name in _STATUS_BUCKETS:
        n = counts.get(name, 0)
        if n:
            items.append(
                {
                    "status": name,
                    "count": n,
                    "ratio": round(n / total * 100, 1),
                }
            )
    for name, n in counts.items():
        if name not in _STATUS_BUCKETS and n:
            items.append(
                {
                    "status": name,
                    "count": n,
                    "ratio": round(n / total * 100, 1),
                }
            )
    return {"total": total, "items": items}


@router.get(
    "/oee",
    summary="设备综合 OEE",
    description="对近期 OEE 快照求平均，返回可用率、性能率、质量率与 OEE（百分数）。",
)
def device_oee(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    date_from, date_to = _normalize_equipment_oee_date_range(today, today)
    items = _build_equipment_oee_report_items(
        db, date_from, date_to, workshop=None, equipment_type=None, equipment_id=None
    )
    if not items:
        date_from, date_to = _normalize_equipment_oee_date_range(None, None)
        items = _build_equipment_oee_report_items(
            db, date_from, date_to, workshop=None, equipment_type=None, equipment_id=None
        )
    summary = _build_equipment_oee_summary(items)
    return {
        "availability": float(summary.availability),
        "performance": float(summary.performance),
        "quality": float(summary.quality),
        "oee": float(summary.oee),
        "utilization_rate": float(summary.utilization_rate),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }


@router.get(
    "/utilization",
    summary="设备利用率趋势",
    description="按日/周/月返回稼动率（利用率）趋势序列，数据来自 OEE 报表聚合。",
)
def device_utilization(
    period: str = Query("day", description="day | week | month"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    p = (period or "day").lower()
    if p == "week":
        date_from = today - timedelta(days=6)
    elif p == "month":
        date_from = today - timedelta(days=29)
    else:
        date_from = today - timedelta(days=9)
    date_to = today
    items = _build_equipment_oee_report_items(
        db, date_from, date_to, workshop=None, equipment_type=None, equipment_id=None
    )
    trend = _build_equipment_oee_trend(items)
    labels = [pt.period_date.strftime("%m-%d") for pt in trend]
    values = [float(pt.utilization_rate) for pt in trend]
    return {"period": p, "labels": labels, "values": values}


@router.get(
    "/alarms/trend",
    summary="设备告警趋势",
    description="近 10 日告警数量趋势；可选返回按告警类型分布。",
)
def device_alarms_trend(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    start_day = today - timedelta(days=9)
    start_dt = datetime.combine(start_day, datetime.min.time())
    rows = (
        db.query(func.date(EquipmentAlarm.occurred_at).label("d"), func.count(EquipmentAlarm.id))
        .filter(EquipmentAlarm.occurred_at >= start_dt)
        .group_by(func.date(EquipmentAlarm.occurred_at))
        .all()
    )
    by_day: dict[str, int] = {}
    for d, c in rows:
        if not d:
            continue
        key = d.isoformat() if isinstance(d, date) else str(d)[:10]
        by_day[key] = int(c)
    labels: list[str] = []
    values: list[int] = []
    for i in range(10):
        d = start_day + timedelta(days=i)
        labels.append(d.strftime("%m-%d"))
        values.append(by_day.get(d.isoformat(), 0))

    type_rows = (
        db.query(EquipmentAlarm.alarm_type, func.count(EquipmentAlarm.id))
        .filter(EquipmentAlarm.occurred_at >= start_dt)
        .group_by(EquipmentAlarm.alarm_type)
        .all()
    )
    by_type = {str(t or "其他"): int(c) for t, c in type_rows}
    return {"labels": labels, "values": values, "by_type": by_type}


@router.get(
    "/list",
    summary="设备看板列表",
    description="分页列出设备，附累计运行小时与最近告警时间。",
)
def device_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="设备状态筛选"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment)
    if status and status != "全部":
        query = query.filter(Equipment.status == status)
    total = query.count()
    equipment_rows = (
        query.order_by(Equipment.equipment_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    ids = [eq.id for eq in equipment_rows]
    runtime_map: dict[int, float] = defaultdict(float)
    if ids:
        for eq_id, hours in (
            db.query(EquipmentRuntimeLog.equipment_id, func.sum(EquipmentRuntimeLog.runtime_hours))
            .filter(EquipmentRuntimeLog.equipment_id.in_(ids))
            .group_by(EquipmentRuntimeLog.equipment_id)
            .all()
        ):
            runtime_map[int(eq_id)] = float(hours or 0)
    last_alarm: dict[int, datetime | None] = {}
    if ids:
        for eq_id, occurred in (
            db.query(EquipmentAlarm.equipment_id, func.max(EquipmentAlarm.occurred_at))
            .filter(EquipmentAlarm.equipment_id.in_(ids))
            .group_by(EquipmentAlarm.equipment_id)
            .all()
        ):
            last_alarm[int(eq_id)] = occurred

    items = []
    for eq in equipment_rows:
        items.append(
            {
                "id": eq.id,
                "equipment_code": eq.equipment_code,
                "name": eq.name,
                "status": eq.status,
                "department": eq.department,
                "location": eq.location,
                "runtime_hours": round(runtime_map.get(eq.id, 0.0), 2),
                "last_alarm_at": (
                    last_alarm[eq.id].isoformat() if last_alarm.get(eq.id) else None
                ),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/output",
    summary="设备产量排行",
    description="返回各设备今日与本周产量，按今日产量排序。",
)
def device_output_ranking(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    rows = db.query(Equipment).order_by(Equipment.equipment_code).all()
    ids = [eq.id for eq in rows]
    today_map: dict[int, int] = defaultdict(int)
    week_map: dict[int, int] = defaultdict(int)
    if ids:
        for eq_id, qty in (
            db.query(EquipmentOutputRecord.equipment_id, func.sum(EquipmentOutputRecord.output_qty))
            .filter(
                EquipmentOutputRecord.equipment_id.in_(ids),
                EquipmentOutputRecord.record_date == today,
            )
            .group_by(EquipmentOutputRecord.equipment_id)
            .all()
        ):
            today_map[int(eq_id)] = int(qty or 0)
        for eq_id, qty in (
            db.query(EquipmentOutputRecord.equipment_id, func.sum(EquipmentOutputRecord.output_qty))
            .filter(
                EquipmentOutputRecord.equipment_id.in_(ids),
                EquipmentOutputRecord.record_date >= week_start,
                EquipmentOutputRecord.record_date <= today,
            )
            .group_by(EquipmentOutputRecord.equipment_id)
            .all()
        ):
            week_map[int(eq_id)] = int(qty or 0)

    items = []
    for eq in rows:
        items.append(
            {
                "equipment_id": eq.id,
                "equipment_code": eq.equipment_code,
                "name": eq.name,
                "today_output": today_map.get(eq.id, 0),
                "week_output": week_map.get(eq.id, 0),
            }
        )
    items.sort(key=lambda x: (-x["today_output"], x["equipment_code"]))
    return {"items": items}
