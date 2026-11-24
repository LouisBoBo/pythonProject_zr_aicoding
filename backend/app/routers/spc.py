"""SPC 控制图接口（表已就绪，补齐查询与计算交付）。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import engine, get_db
from app.models import User
from app.permissions import QUALITY_WRITE, require_permissions
from app.schemas_spc import (
    SpcChartDetailResponse,
    SpcChartListItem,
    SpcChartListResponse,
    SpcComputeRequest,
    SpcComputeResponse,
    SpcFiltersResponse,
    SpcPointItem,
)
from app.spc_store import (
    SpcChart,
    SpcMeasurement,
    compute_chart,
    ensure_spc_schema,
    recompute_chart_from_measurements,
)

router = APIRouter(prefix="/api/quality/spc", tags=["SPC控制图"])

ensure_spc_schema(engine)


def _sample_counts(db: Session) -> dict[int, int]:
    rows = (
        db.query(SpcMeasurement.chart_id, func.count(SpcMeasurement.id))
        .group_by(SpcMeasurement.chart_id)
        .all()
    )
    return {int(r[0]): int(r[1]) for r in rows}


def _parse_points(raw: str | None) -> list[SpcPointItem]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        data = []
    points: list[SpcPointItem] = []
    for p in data:
        if not isinstance(p, dict):
            continue
        points.append(
            SpcPointItem(
                index=int(p.get("index") or 0),
                value=float(p.get("value") or 0),
                out_of_control=bool(p.get("out_of_control")),
                range=p.get("range"),
                measured_at=p.get("measured_at"),
                sample_label=p.get("sample_label"),
            )
        )
    return points


def _detail_response(db: Session, chart: SpcChart, result: dict | None = None) -> SpcChartDetailResponse:
    points = _parse_points(chart.data_points)
    out_idx = (
        result.get("out_of_control_indexes")
        if result
        else [p.index for p in points if p.out_of_control]
    )
    sample_count = (
        db.query(func.count(SpcMeasurement.id))
        .filter(SpcMeasurement.chart_id == chart.id)
        .scalar()
        or 0
    )
    return SpcChartDetailResponse(
        id=chart.id,
        chart_code=chart.chart_code,
        chart_name=chart.chart_name,
        process_name=chart.process_name,
        characteristic=chart.characteristic,
        chart_type=chart.chart_type,
        subgroup_size=chart.subgroup_size,
        unit=chart.unit,
        usl=chart.usl,
        lsl=chart.lsl,
        target=chart.target,
        ucl=chart.ucl,
        cl=chart.cl,
        lcl=chart.lcl,
        cp=chart.cp,
        cpk=chart.cpk,
        status=chart.status,
        sample_count=int(sample_count),
        points=points,
        out_of_control_indexes=out_idx or [],
        updated_at=chart.updated_at,
    )


@router.get(
    "/filters",
    response_model=SpcFiltersResponse,
    summary="SPC 筛选项",
    description="返回工序、质量特性与图类型下拉选项，供 SPC 控制图页筛选。",
)
def spc_filters(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    processes = [
        r[0]
        for r in db.query(SpcChart.process_name).distinct().order_by(SpcChart.process_name).all()
        if r[0]
    ]
    chars = [
        r[0]
        for r in db.query(SpcChart.characteristic).distinct().order_by(SpcChart.characteristic).all()
        if r[0]
    ]
    types = [
        r[0]
        for r in db.query(SpcChart.chart_type).distinct().order_by(SpcChart.chart_type).all()
        if r[0]
    ]
    return SpcFiltersResponse(
        process_names=processes,
        characteristics=chars,
        chart_types=types or ["I-MR", "Xbar-R"],
    )


@router.get(
    "/charts",
    response_model=SpcChartListResponse,
    summary="SPC 控制图列表",
    description="分页/筛选查询 SPC 控制图配置及最近一次控制限、Cp/Cpk 与状态。",
)
def list_spc_charts(
    process_name: str | None = Query(None, description="工序名称"),
    characteristic: str | None = Query(None, description="质量特性"),
    chart_type: str | None = Query(None, description="图类型 I-MR / Xbar-R"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SpcChart)
    if process_name:
        q = q.filter(SpcChart.process_name == process_name)
    if characteristic:
        q = q.filter(SpcChart.characteristic == characteristic)
    if chart_type:
        q = q.filter(SpcChart.chart_type == chart_type)
    rows = q.order_by(SpcChart.id.asc()).all()
    counts = _sample_counts(db)
    items = [
        SpcChartListItem(
            id=r.id,
            chart_code=r.chart_code,
            chart_name=r.chart_name,
            process_name=r.process_name,
            characteristic=r.characteristic,
            chart_type=r.chart_type,
            subgroup_size=r.subgroup_size,
            unit=r.unit,
            usl=r.usl,
            lsl=r.lsl,
            target=r.target,
            ucl=r.ucl,
            cl=r.cl,
            lcl=r.lcl,
            cp=r.cp,
            cpk=r.cpk,
            status=r.status,
            sample_count=counts.get(r.id, 0),
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return SpcChartListResponse(items=items, total=len(items))


@router.get(
    "/charts/{chart_id}",
    response_model=SpcChartDetailResponse,
    summary="SPC 控制图详情",
    description="返回单张控制图的数据点、UCL/CL/LCL、规格限与过程能力（只读，不落库）。",
)
def get_spc_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    chart = db.query(SpcChart).filter(SpcChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="控制图不存在")
    return _detail_response(db, chart)


@router.post(
    "/charts/{chart_id}/recompute",
    response_model=SpcChartDetailResponse,
    summary="重新计算 SPC 控制限",
    description="基于测量点重算并持久化 UCL/CL/LCL 与 Cp/Cpk；需 quality.write 权限。",
)
def recompute_spc_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(QUALITY_WRITE)),
):
    _ = current_user
    chart = db.query(SpcChart).filter(SpcChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="控制图不存在")
    result = recompute_chart_from_measurements(db, chart)
    return _detail_response(db, chart, result=result)


@router.post(
    "/compute",
    response_model=SpcComputeResponse,
    summary="临时计算 SPC 控制限",
    description="对传入测量序列即时计算 I-MR 或 X̄-R 控制限与 Cp/Cpk，不落库（最多 5000 点）。",
)
def compute_spc(
    body: SpcComputeRequest,
    _: User = Depends(get_current_user),
):
    result = compute_chart(
        [float(v) for v in body.values],
        chart_type=body.chart_type,
        subgroup_size=body.subgroup_size,
        usl=body.usl,
        lsl=body.lsl,
    )
    points = [
        SpcPointItem(
            index=int(p.get("index") or 0),
            value=float(p.get("value") or 0),
            out_of_control=bool(p.get("out_of_control")),
            range=p.get("range"),
        )
        for p in (result.get("points") or [])
    ]
    return SpcComputeResponse(
        chart_type=body.chart_type,
        sample_count=int(result.get("sample_count") or 0),
        ucl=result.get("ucl"),
        cl=result.get("cl"),
        lcl=result.get("lcl"),
        cp=result.get("cp"),
        cpk=result.get("cpk"),
        status=result.get("status") or "normal",
        points=points,
        out_of_control_indexes=result.get("out_of_control_indexes") or [],
    )
