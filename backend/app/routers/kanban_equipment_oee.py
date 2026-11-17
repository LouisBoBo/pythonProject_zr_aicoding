"""设备 OEE 看板 — 按时间窗口聚合 KPI 与设备排行。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.routers.reports import (
    _average_metric,
    _build_equipment_oee_report_items,
    _build_equipment_oee_summary,
    _empty_equipment_oee_summary,
)

router = APIRouter(prefix="/api/kanban", tags=["kanban-equipment-oee"])


def _oee_period_bounds(period: str) -> tuple[date, date]:
    today = date.today()
    p = (period or "day").lower()
    if p == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if p == "month":
        start = today.replace(day=1)
        return start, today
    return today, today


def _aggregate_ranking_by_equipment(items) -> list[dict]:
    grouped: dict[str, list] = defaultdict(list)
    meta: dict[str, dict] = {}
    for item in items:
        grouped[item.equipment_code].append(item)
        if item.equipment_code not in meta:
            meta[item.equipment_code] = {
                "equipment_name": item.equipment_name,
                "workshop": item.workshop,
                "equipment_type": item.equipment_type,
            }

    rows: list[dict] = []
    for code, bucket in grouped.items():
        info = meta.get(code, {})
        rows.append(
            {
                "equipment_code": code,
                "equipment_name": info.get("equipment_name") or code,
                "workshop": info.get("workshop"),
                "equipment_type": info.get("equipment_type"),
                "availability": _average_metric([r.availability for r in bucket]),
                "performance": _average_metric([r.performance for r in bucket]),
                "quality": _average_metric([r.quality for r in bucket]),
                "oee": _average_metric([r.oee for r in bucket]),
            }
        )
    rows.sort(key=lambda r: (-r["oee"], r["equipment_code"]))
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


@router.get(
    "/equipment-oee",
    summary="设备 OEE 看板",
    description=(
        "按今日/本周/本月聚合全厂 OEE KPI（时间稼动率、性能稼动率、良品率、OEE），"
        "并返回各设备 OEE 排行及柱状图序列。"
    ),
)
def equipment_oee_kanban(
    period: str = Query("day", pattern="^(day|week|month)$", description="day | week | month"),
    limit: int = Query(20, ge=1, le=100, description="排行最多返回条数"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    date_from, date_to = _oee_period_bounds(period)
    items = _build_equipment_oee_report_items(
        db, date_from, date_to, workshop=None, equipment_type=None, equipment_id=None
    )
    if not items:
        empty = _empty_equipment_oee_summary()
        return {
            "period": period,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "summary": {
                "availability": float(empty.availability),
                "performance": float(empty.performance),
                "quality": float(empty.quality),
                "oee": float(empty.oee),
            },
            "ranking": [],
            "chart": {"labels": [], "values": []},
        }

    summary = _build_equipment_oee_summary(items)
    ranking = _aggregate_ranking_by_equipment(items)[:limit]
    top_for_chart = ranking[:10]
    return {
        "period": period,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "summary": {
            "availability": float(summary.availability),
            "performance": float(summary.performance),
            "quality": float(summary.quality),
            "oee": float(summary.oee),
        },
        "ranking": ranking,
        "chart": {
            "labels": [r["equipment_name"] for r in top_for_chart],
            "values": [r["oee"] for r in top_for_chart],
        },
    }
