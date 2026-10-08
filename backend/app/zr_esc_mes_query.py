"""PCB 生产运营分析：本地库聚合（MES 连接器未配置时仍可出数）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import EmployeeWorkHour, ProductionOutputRecord, QualityAnomaly, WorkOrder
from app.work_order_utils import calc_wip_quantity, derive_current_process

_BLIND_SPOTS = [
    "作废口径未接入",
    "达产率",
    "稼动率",
    "工序良率",
    "库存时间戳",
]


def query_pcb_production_ops(db: Session, *, days: int = 7) -> dict:
    today = date.today()
    requested_to = today
    requested_from = today - timedelta(days=days - 1)

    output_trend: list[dict] = []
    for i in range(days):
        d = requested_from + timedelta(days=i)
        day_start = datetime.combine(d, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        wo_count = (
            db.query(func.count(WorkOrder.id))
            .filter(
                WorkOrder.start_date == d,
            )
            .scalar()
            or 0
        )
        plan_qty = (
            db.query(func.coalesce(func.sum(WorkOrder.plan_quantity), 0))
            .filter(WorkOrder.start_date == d)
            .scalar()
            or 0
        )
        actual_qty = int(
            db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
            .filter(
                ProductionOutputRecord.record_at >= day_start,
                ProductionOutputRecord.record_at < day_end,
            )
            .scalar()
            or 0
        )
        work_hours = float(
            db.query(func.coalesce(func.sum(EmployeeWorkHour.work_hours), 0))
            .filter(EmployeeWorkHour.work_date == d)
            .scalar()
            or 0
        )
        output_trend.append(
            {
                "stat_date": d.isoformat(),
                "work_order_count": int(wo_count),
                "plan_qty": int(plan_qty),
                "actual_qty": actual_qty,
                "work_hours": round(work_hours, 2),
            }
        )

    trend_dates = [row["stat_date"] for row in output_trend if row["work_order_count"] or row["actual_qty"]]
    if trend_dates:
        aligned_from = min(trend_dates)
        aligned_to = max(trend_dates)
    else:
        aligned_from = requested_from.isoformat()
        aligned_to = requested_to.isoformat()

    wip_rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.status.in_(("pending", "in_progress")))
        .order_by(WorkOrder.updated_at.desc())
        .limit(10)
        .all()
    )
    wip_orders = []
    for wo in wip_rows:
        wip_qty = calc_wip_quantity(wo.plan_quantity, wo.actual_quantity)
        process = wo.current_process or derive_current_process(
            wo.status, wo.plan_quantity, wo.actual_quantity
        )
        wip_orders.append(
            {
                "order_no": wo.order_no,
                "product_name": wo.product_name,
                "current_process": process,
                "wip_quantity": wip_qty,
                "plan_quantity": wo.plan_quantity,
                "actual_quantity": wo.actual_quantity,
                "actual_work_hours": None,
                "check_result": "待核",
            }
        )

    abnormal_rows = (
        db.query(QualityAnomaly)
        .filter(QualityAnomaly.status == "open")
        .order_by(QualityAnomaly.discovered_at.desc())
        .limit(3)
        .all()
    )
    abnormal_orders = [
        {
            "production_line": row.production_line,
            "process": row.process,
            "defect_type": row.defect_type,
            "severity": row.severity,
            "discovered_at": row.discovered_at.isoformat(sep=" ", timespec="seconds")
            if row.discovered_at
            else "",
            "check_result": "待核",
        }
        for row in abnormal_rows
    ]

    return {
        "mes_status": {
            "base_url": "local-sqlite",
            "reachable": True,
            "mes_status": "normal",
            "message": "使用本库工单/产出/工时/品质异常聚合",
        },
        "data_source": "employee_work_hours + production_output_records + work_orders",
        "time_window": {
            "requested_from": requested_from.isoformat(),
            "requested_to": requested_to.isoformat(),
            "aligned_from": aligned_from,
            "aligned_to": aligned_to,
        },
        "output_trend": output_trend,
        "wip_orders": wip_orders,
        "abnormal_orders": abnormal_orders,
        "blind_spots": list(_BLIND_SPOTS),
    }
