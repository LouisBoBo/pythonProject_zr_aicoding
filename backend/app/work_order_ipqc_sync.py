"""从 IPQC 检验记录回填业务工单（幂等）。

清掉 WO-AN-* 演示单后，用检验记录里的真实 work_order_no 重建工单池，
并回写 quality_inspection_records.work_order_id，避免列表空、报工/桥接断链。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WorkOrder
from app.process_catalog import STANDARD_PROCESSES, normalize_process_name
from app.quality_inspection_record_store import QualityInspectionRecord
from app.work_order_utils import derive_current_process

_PROCESS_LINE = {
    "钻孔": "钻孔线",
    "蚀刻": "蚀刻线",
    "阻焊": "阻焊线",
    "成型": "成型线",
    "待确认工序": "PCB产线",
}

_ASSIGNEES = ["张工", "李工", "王工", "赵工", "钱工", "孙工", "周工", "吴工"]


def _stable_pick(seed: str, items: list[str]) -> str:
    h = 0
    for ch in seed:
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return items[h % len(items)] if items else ""


def _derive_status(min_d: date, max_d: date, today: date) -> str:
    if max_d >= today:
        return "in_progress"
    if max_d >= today - timedelta(days=2):
        return "completed"
    if min_d >= today - timedelta(days=7):
        return "completed"
    return "closed"


def ensure_work_orders_from_ipqc(db: Session | None = None) -> dict:
    """按 IPQC 的 work_order_no 补齐工单；已存在则更新关键字段，不删业务手工单。"""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        today = date.today()
        now = datetime.now()

        # 聚合检验记录 → 工单画像
        rows = (
            db.query(
                QualityInspectionRecord.work_order_no,
                func.min(QualityInspectionRecord.inspected_at).label("min_at"),
                func.max(QualityInspectionRecord.inspected_at).label("max_at"),
                func.count().label("insp_n"),
                func.sum(
                    func.coalesce(QualityInspectionRecord.inspected_qty, 1)
                ).label("qty_sum"),
                func.max(QualityInspectionRecord.product_code).label("product_code"),
                func.max(QualityInspectionRecord.material_name).label("material_name"),
                func.max(QualityInspectionRecord.process_name).label("process_name"),
                func.max(QualityInspectionRecord.customer_code).label("customer_code"),
            )
            .filter(
                QualityInspectionRecord.work_order_no.isnot(None),
                QualityInspectionRecord.work_order_no != "",
            )
            .group_by(QualityInspectionRecord.work_order_no)
            .all()
        )

        existing = {
            wo.order_no: wo
            for wo in db.query(WorkOrder).filter(
                WorkOrder.order_no.in_([r[0] for r in rows if r[0]])
            ).all()
        } if rows else {}

        created = 0
        updated = 0
        for (
            order_no,
            min_at,
            max_at,
            insp_n,
            qty_sum,
            product_code,
            material_name,
            process_name,
            customer_code,
        ) in rows:
            order_no = (order_no or "").strip()
            if not order_no:
                continue
            min_d = min_at.date() if hasattr(min_at, "date") else today
            max_d = max_at.date() if hasattr(max_at, "date") else today
            process = normalize_process_name(process_name) or STANDARD_PROCESSES[0]
            line = _PROCESS_LINE.get(process, "PCB产线")
            code = (product_code or "").strip() or None
            name = (material_name or "").strip()
            if not name:
                name = f"料号 {code[-10:]}" if code and len(code) > 10 else (code or "PCB 产品")
            plan_qty = max(int(qty_sum or insp_n or 1), int(insp_n or 1))
            status = _derive_status(min_d, max_d, today)
            actual = plan_qty if status in ("completed", "closed") else max(int(plan_qty * 0.6), 1)
            if status == "in_progress":
                actual = max(int(plan_qty * 0.75), 1)
            priority = "high" if (insp_n or 0) >= 8 else "normal"
            assignee = _stable_pick(order_no, _ASSIGNEES)
            remark = f"IPQC 回填；客户 {customer_code or '-'}；检验 {int(insp_n or 0)} 笔"

            wo = existing.get(order_no)
            if wo is None:
                wo = WorkOrder(
                    order_no=order_no,
                    product_name=name[:100],
                    product_code=code[:50] if code else None,
                    production_line=line,
                    plan_quantity=plan_qty,
                    actual_quantity=actual,
                    status=status,
                    priority=priority,
                    assignee=assignee,
                    start_date=min_d,
                    end_date=max_d if status in ("completed", "closed") else max_d + timedelta(days=2),
                    actual_start_time=min_at if isinstance(min_at, datetime) else datetime.combine(min_d, datetime.min.time()),
                    actual_end_time=(
                        max_at
                        if status in ("completed", "closed") and isinstance(max_at, datetime)
                        else None
                    ),
                    current_process=process,
                    remark=remark[:500],
                    created_at=min_at if isinstance(min_at, datetime) else now,
                    updated_at=now,
                )
                # 完工/关闭补齐工序为末道
                if not wo.current_process:
                    wo.current_process = derive_current_process(
                        wo.status, wo.plan_quantity, wo.actual_quantity
                    )
                db.add(wo)
                created += 1
            else:
                wo.product_name = name[:100]
                wo.product_code = code[:50] if code else wo.product_code
                wo.production_line = line
                wo.plan_quantity = max(wo.plan_quantity or 0, plan_qty)
                if status in ("completed", "closed"):
                    wo.actual_quantity = max(wo.actual_quantity or 0, actual)
                    wo.status = status
                    wo.end_date = max_d
                    if isinstance(max_at, datetime):
                        wo.actual_end_time = max_at
                wo.current_process = process
                wo.remark = remark[:500]
                wo.updated_at = now
                updated += 1

        db.flush()

        # 回写检验记录 work_order_id
        wo_map = {
            order_no: wid
            for wid, order_no in db.query(WorkOrder.id, WorkOrder.order_no).all()
        }
        linked = 0
        pending = (
            db.query(QualityInspectionRecord)
            .filter(
                QualityInspectionRecord.work_order_no.isnot(None),
                QualityInspectionRecord.work_order_no != "",
                QualityInspectionRecord.work_order_id.is_(None),
            )
            .all()
        )
        for row in pending:
            wid = wo_map.get((row.work_order_no or "").strip())
            if wid:
                row.work_order_id = wid
                linked += 1

        if own:
            db.commit()
        else:
            db.flush()

        return {
            "ipqc_orders": len(rows),
            "created": created,
            "updated": updated,
            "linked_inspections": linked,
            "work_orders_total": db.query(WorkOrder).count(),
        }
    except Exception:
        if own:
            db.rollback()
        raise
    finally:
        if own:
            db.close()
