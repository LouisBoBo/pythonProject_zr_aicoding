"""用 IPQC 检验记录重建 / 对齐 quality_metrics，保证工序口径一致。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import QualityAnomaly, QualityDefectDetail, QualityMetrics, WorkOrder, WorkOrderLaborRecord
from app.process_catalog import (
    IPQC_METRICS_LINE,
    LEGACY_PROCESS_ALIASES,
    QUALITY_DEFECT_TYPES,
    QUALITY_PROCESSES,
    normalize_process_name,
)
from app.quality_inspection_record_store import QualityInspectionRecord
from app.work_order_utils import derive_current_process


def _pass_expr():
    return case(
        (
            (QualityInspectionRecord.source_result == 1)
            | (func.lower(func.coalesce(QualityInspectionRecord.inspection_result, "")).in_(("pass", "ok"))),
            1,
        ),
        else_=0,
    )


def _fail_expr():
    return case(
        (
            (QualityInspectionRecord.source_result == 2)
            | (
                func.lower(func.coalesce(QualityInspectionRecord.inspection_result, "")).in_(
                    ("fail", "ng")
                )
            ),
            1,
        ),
        else_=0,
    )


def rebuild_quality_metrics_from_ipqc(db: Session, *, days: int | None = None) -> dict:
    """按日×工序用 IPQC 重建 quality_metrics。

    - 删除旧 SMT 工序（贴片/AOI…）及同名 PCB 产线汇总，避免混口径
    - 有检验实据的日写入实数；缺口日由调用方 backfill 用 QUALITY_PROCESSES 补齐
    """
    today = date.today()
    if days is None:
        days = max((today - date(today.year, today.month, 1)).days + 1, 30)
    start = today - timedelta(days=days - 1)

    legacy_names = list(LEGACY_PROCESS_ALIASES.keys())
    # 清掉旧 SMT 工序名；清掉非 PCB 产线汇总（SMT/组装/测试/DIP 挂 PCB 工序是口径冲突）
    if legacy_names:
        (
            db.query(QualityMetrics)
            .filter(QualityMetrics.process.in_(legacy_names))
            .delete(synchronize_session=False)
        )
    (
        db.query(QualityMetrics)
        .filter(QualityMetrics.production_line != IPQC_METRICS_LINE)
        .delete(synchronize_session=False)
    )
    (
        db.query(QualityMetrics)
        .filter(
            QualityMetrics.production_line == IPQC_METRICS_LINE,
            QualityMetrics.record_date >= start,
        )
        .delete(synchronize_session=False)
    )

    day_expr = func.date(QualityInspectionRecord.inspected_at)
    proc_expr = func.nullif(QualityInspectionRecord.process_name, "")
    rows = (
        db.query(
            day_expr.label("day"),
            proc_expr.label("pname"),
            func.count().label("total"),
            func.sum(_pass_expr()).label("pass_cnt"),
            func.sum(_fail_expr()).label("fail_cnt"),
        )
        .filter(
            QualityInspectionRecord.inspected_at.isnot(None),
            QualityInspectionRecord.inspected_at
            >= datetime.combine(start, datetime.min.time()),
            QualityInspectionRecord.process_name.isnot(None),
            QualityInspectionRecord.process_name != "",
        )
        .group_by(day_expr, proc_expr)
        .all()
    )

    inserted = 0
    for day, pname, total, pass_cnt, fail_cnt in rows:
        if day is None or not pname:
            continue
        process = normalize_process_name(str(pname))
        if not process:
            continue
        # 统一到标准目录；非标准名仍保留，便于发现新工序
        total_i = int(total or 0)
        if total_i <= 0:
            continue
        pass_i = int(pass_cnt or 0)
        fail_i = int(fail_cnt or 0)
        # pending 等计入 total，但不算良/不良时用 remainder 进 good 更稳妥
        judged = pass_i + fail_i
        good = pass_i if judged > 0 else max(total_i - fail_i, 0)
        scrap = 0
        record_date = day if isinstance(day, date) else date.fromisoformat(str(day)[:10])
        db.add(
            QualityMetrics(
                record_date=record_date,
                production_line=IPQC_METRICS_LINE,
                process=process,
                good_count=good,
                defect_count=fail_i,
                scrap_count=scrap,
                total_inspected=total_i,
            )
        )
        inserted += 1

    db.flush()
    return {"days": days, "inserted": inserted, "start": start.isoformat()}


def align_quality_process_names(db: Session) -> dict:
    """把异常 / 缺陷 / 报工 / 工单当前工序上的旧 SMT 名改成 IPQC 口径。"""
    anomaly_n = 0
    for row in db.query(QualityAnomaly).all():
        mapped = normalize_process_name(row.process)
        if mapped and mapped != row.process:
            row.process = mapped
            anomaly_n += 1

    defect_n = 0
    for row in db.query(QualityDefectDetail).all():
        mapped = normalize_process_name(row.process)
        if mapped and mapped != row.process:
            row.process = mapped
            defect_n += 1

    labor_n = 0
    for row in db.query(WorkOrderLaborRecord).all():
        mapped = normalize_process_name(row.process)
        if mapped and mapped != row.process:
            row.process = mapped
            labor_n += 1

    wo_n = 0
    for wo in db.query(WorkOrder).all():
        if wo.current_process:
            mapped = normalize_process_name(wo.current_process)
            if mapped and mapped != wo.current_process:
                wo.current_process = mapped
                wo_n += 1
        else:
            wo.current_process = derive_current_process(
                wo.status, wo.plan_quantity or 0, wo.actual_quantity or 0
            )
            wo_n += 1

    return {
        "anomalies_updated": anomaly_n,
        "defects_updated": defect_n,
        "labor_updated": labor_n,
        "work_orders_updated": wo_n,
    }


def sync_quality_process_alignment(*, days: int | None = None) -> dict:
    """对齐入口：重建 metrics + 改写异常/缺陷工序名。"""
    db = SessionLocal()
    try:
        metrics = rebuild_quality_metrics_from_ipqc(db, days=days)
        names = align_quality_process_names(db)
        db.commit()
        return {**metrics, **names}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
