"""设备停机报表：按 equipment_runtime_logs 停机时段查询。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Equipment, EquipmentRuntimeLog, LineCapacitySnapshot, ProductionLine, User

router = APIRouter(prefix="/api/reports", tags=["报表中心"])

DOWNTIME_STATUS = "停机"


class EquipmentDowntimeFilterEquipment(BaseModel):
    id: int
    equipment_code: str
    name: str
    workshop: str | None = None
    production_line: str | None = None


class EquipmentDowntimeFiltersResponse(BaseModel):
    workshops: list[str] = Field(description="车间列表（设备所属部门）")
    production_lines: list[str] = Field(description="产线名称列表")
    downtime_reasons: list[str] = Field(description="停机原因选项")
    equipment: list[EquipmentDowntimeFilterEquipment] = Field(description="设备下拉")


class EquipmentDowntimeReportSummary(BaseModel):
    event_count: int = Field(description="停机次数合计")
    total_duration_hours: float = Field(description="停机时长合计（小时）")


class EquipmentDowntimeReportItem(BaseModel):
    id: int
    equipment_id: int
    equipment_code: str | None = None
    equipment_name: str | None = None
    workshop: str | None = None
    production_line: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    duration_hours: float = Field(description="停机时长（小时）")
    downtime_reason: str | None = None


class EquipmentDowntimeReportListResponse(BaseModel):
    items: list[EquipmentDowntimeReportItem]
    total: int
    page: int
    page_size: int
    summary: EquipmentDowntimeReportSummary


def _normalize_downtime_date_range(
    date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    today = date.today()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = date_to - timedelta(days=6)
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _duration_hours(log: EquipmentRuntimeLog) -> float:
    if log.runtime_hours is not None:
        hours = float(log.runtime_hours)
        if hours > 0:
            return round(hours, 2)
    if log.start_at and log.end_at:
        minutes = (log.end_at - log.start_at).total_seconds() / 3600
        if minutes > 0:
            return round(minutes, 2)
    return 0.0


def _build_equipment_production_line_map(db: Session) -> dict[int, str | None]:
    """按设备名称/位置与产线匹配，与日产报表设备解析逻辑一致。"""
    lines = db.query(ProductionLine).order_by(ProductionLine.id).all()
    equipment_list = db.query(Equipment).order_by(Equipment.id).all()
    if not equipment_list:
        return {}

    snaps = (
        db.query(LineCapacitySnapshot)
        .order_by(LineCapacitySnapshot.snapshot_at.desc())
        .all()
    )
    snap_by_line: dict[int, str | None] = {}
    for snap in snaps:
        if snap.production_line_id not in snap_by_line:
            label = (snap.station_name or "").replace("-主工位", "").strip() or None
            snap_by_line[snap.production_line_id] = label

    result: dict[int, str | None] = {}
    for eq in equipment_list:
        matched: list[str] = []
        for line in lines:
            loc = eq.location or ""
            name = eq.name or ""
            if line.name in loc or line.name in name:
                matched.append(line.name)
        if matched:
            result[eq.id] = "、".join(sorted(set(matched)))
            continue
        for line in lines:
            snap_label = snap_by_line.get(line.id)
            if snap_label and (snap_label in (eq.name or "") or snap_label in (eq.location or "")):
                matched.append(line.name)
        result[eq.id] = "、".join(sorted(set(matched))) if matched else None
    return result


def _equipment_ids_for_production_line(
    db: Session, production_line: str, line_map: dict[int, str | None] | None = None
) -> list[int]:
    if line_map is None:
        line_map = _build_equipment_production_line_map(db)
    return [
        eq_id
        for eq_id, line_name in line_map.items()
        if line_name and production_line in line_name.split("、")
    ]


def _apply_equipment_downtime_filters(
    query,
    *,
    db: Session,
    date_from: date,
    date_to: date,
    workshop: str | None,
    equipment_id: int | None,
    production_line: str | None,
    downtime_reason: str | None,
    line_map: dict[int, str | None],
):
    day_start = datetime.combine(date_from, datetime.min.time())
    day_end = datetime.combine(date_to + timedelta(days=1), datetime.min.time())
    query = query.filter(
        EquipmentRuntimeLog.status == DOWNTIME_STATUS,
        EquipmentRuntimeLog.start_at >= day_start,
        EquipmentRuntimeLog.start_at < day_end,
    )
    query = query.join(Equipment, EquipmentRuntimeLog.equipment_id == Equipment.id)
    if workshop:
        query = query.filter(Equipment.department == workshop)
    if equipment_id:
        query = query.filter(EquipmentRuntimeLog.equipment_id == equipment_id)
    if downtime_reason:
        query = query.filter(EquipmentRuntimeLog.downtime_reason == downtime_reason)
    if production_line:
        eq_ids = _equipment_ids_for_production_line(
            db, production_line, line_map=line_map
        )
        if not eq_ids:
            query = query.filter(EquipmentRuntimeLog.id == -1)
        else:
            query = query.filter(EquipmentRuntimeLog.equipment_id.in_(eq_ids))
    return query


def _to_report_item(
    log: EquipmentRuntimeLog,
    equipment: Equipment | None,
    production_line: str | None,
) -> EquipmentDowntimeReportItem:
    return EquipmentDowntimeReportItem(
        id=log.id,
        equipment_id=log.equipment_id,
        equipment_code=equipment.equipment_code if equipment else None,
        equipment_name=equipment.name if equipment else None,
        workshop=equipment.department if equipment else None,
        production_line=production_line,
        start_at=log.start_at,
        end_at=log.end_at,
        duration_hours=_duration_hours(log),
        downtime_reason=log.downtime_reason or "其他",
    )


@router.get(
    "/equipment-downtime/filters",
    response_model=EquipmentDowntimeFiltersResponse,
    summary="停机报表筛选选项",
    description="返回车间、产线、停机原因与设备下拉，供停机报表筛选使用。",
)
def list_equipment_downtime_filters(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    line_map = _build_equipment_production_line_map(db)
    workshops = sorted(
        {
            dept
            for (dept,) in db.query(Equipment.department)
            .filter(Equipment.department.isnot(None), Equipment.department != "")
            .distinct()
            .all()
            if dept
        }
    )
    production_lines = [
        name for (name,) in db.query(ProductionLine.name).order_by(ProductionLine.id).all()
    ]
    reason_rows = (
        db.query(EquipmentRuntimeLog.downtime_reason)
        .filter(
            EquipmentRuntimeLog.status == DOWNTIME_STATUS,
            EquipmentRuntimeLog.downtime_reason.isnot(None),
            EquipmentRuntimeLog.downtime_reason != "",
        )
        .distinct()
        .all()
    )
    downtime_reasons = sorted({row[0] for row in reason_rows if row[0]})
    if not downtime_reasons:
        downtime_reasons = ["换料", "故障", "待料", "其他"]

    equipment_rows = db.query(Equipment).order_by(Equipment.equipment_code).all()
    equipment = [
        EquipmentDowntimeFilterEquipment(
            id=eq.id,
            equipment_code=eq.equipment_code,
            name=eq.name,
            workshop=eq.department,
            production_line=line_map.get(eq.id),
        )
        for eq in equipment_rows
    ]
    return EquipmentDowntimeFiltersResponse(
        workshops=workshops,
        production_lines=production_lines,
        downtime_reasons=downtime_reasons,
        equipment=equipment,
    )


@router.get(
    "/equipment-downtime",
    response_model=EquipmentDowntimeReportListResponse,
    summary="停机报表",
    description=(
        "按设备停机时段列出明细：设备、产线、停机起止、时长与原因；"
        "数据来自 equipment_runtime_logs（status=停机）；"
        "支持日期区间、车间、产线、设备、停机原因筛选与分页，默认近 7 日。"
    ),
)
def list_equipment_downtime_report(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    date_from: date | None = Query(None, description="停机日期起（含）"),
    date_to: date | None = Query(None, description="停机日期止（含）"),
    workshop: str | None = Query(None, description="车间（设备部门）"),
    production_line: str | None = Query(None, description="产线名称"),
    equipment_id: int | None = Query(None, description="设备 ID"),
    downtime_reason: str | None = Query(None, description="停机原因"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    date_from, date_to = _normalize_downtime_date_range(date_from, date_to)
    line_map = _build_equipment_production_line_map(db)

    base_query = db.query(EquipmentRuntimeLog).options(joinedload(EquipmentRuntimeLog.equipment))
    base_query = _apply_equipment_downtime_filters(
        base_query,
        db=db,
        date_from=date_from,
        date_to=date_to,
        workshop=workshop,
        equipment_id=equipment_id,
        production_line=production_line,
        downtime_reason=downtime_reason,
        line_map=line_map,
    )

    event_count = base_query.count()
    # 汇总时长：仅取时长相关列，避免把全量 ORM 对象载入内存后再切片
    duration_rows = base_query.with_entities(
        EquipmentRuntimeLog.runtime_hours,
        EquipmentRuntimeLog.start_at,
        EquipmentRuntimeLog.end_at,
    ).all()
    total_duration_hours = 0.0
    for runtime_hours, start_at, end_at in duration_rows:
        if runtime_hours is not None and float(runtime_hours) > 0:
            total_duration_hours += float(runtime_hours)
        elif start_at and end_at:
            hours = (end_at - start_at).total_seconds() / 3600
            if hours > 0:
                total_duration_hours += hours
    total_duration_hours = round(total_duration_hours, 2)

    page_logs = (
        base_query.order_by(
            EquipmentRuntimeLog.start_at.desc(),
            EquipmentRuntimeLog.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        _to_report_item(
            log,
            log.equipment,
            line_map.get(log.equipment_id),
        )
        for log in page_logs
    ]

    return EquipmentDowntimeReportListResponse(
        items=items,
        total=event_count,
        page=page,
        page_size=page_size,
        summary=EquipmentDowntimeReportSummary(
            event_count=event_count,
            total_duration_hours=total_duration_hours,
        ),
    )