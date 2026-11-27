"""从 IPQC 检验记录回填业务工单（幂等）。

清掉 WO-AN-* 演示单后，用检验记录里的真实 work_order_no 重建工单池，
并回写 quality_inspection_records.work_order_id，避免列表空、报工/桥接断链。

规则贴近真实 PCB 生产：
- 当前工序 = 最近一次检验工序；完工/关闭取已检工序中流程最靠后的一道
- 计划数量 ≈ 各工序检验量合计的最大值（避免跨工序累加虚高）
- 状态随最近检验日滚动：今日有检→在制；近 2 日→完工；更早→关闭
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import WorkOrder
from app.process_catalog import STANDARD_PROCESSES, normalize_process_name
from app.quality_inspection_record_store import QualityInspectionRecord

_PROCESS_LINE = {
    "钻孔": "钻孔线",
    "蚀刻": "蚀刻线",
    "阻焊": "阻焊线",
    "成型": "成型线",
    "待确认工序": "PCB产线",
}

_PROCESS_RANK = {name: idx for idx, name in enumerate(STANDARD_PROCESSES)}

_ASSIGNEES = ["张工", "李工", "王工", "赵工", "钱工", "孙工", "周工", "吴工"]

# 末道制造工序（完工工单当前工序，不用「待确认工序」）
_LAST_MFG_PROCESS = "成型"


def _stable_pick(seed: str, items: list[str]) -> str:
    h = 0
    for ch in seed:
        h = (h * 131 + ord(ch)) & 0x7FFFFFFF
    return items[h % len(items)] if items else ""


def _derive_status(min_d: date, max_d: date, today: date) -> str:
    """按最近检验日推导工单状态（符合现场：有当日检验即在制）。"""
    if max_d >= today:
        return "in_progress"
    if max_d >= today - timedelta(days=2):
        return "completed"
    if min_d >= today - timedelta(days=7) and max_d >= today - timedelta(days=5):
        return "completed"
    return "closed"


def _pick_current_process(
    *,
    status: str,
    latest_process: str | None,
    processes: set[str],
) -> str:
    """在制看最近检验；完工/关闭取已走过的最靠后工序。"""
    ranked = sorted(
        (p for p in processes if p in _PROCESS_RANK),
        key=lambda p: _PROCESS_RANK[p],
    )
    if status in ("completed", "closed"):
        if ranked:
            # 已到成型或仅有待确认时，完工显示成型
            furthest = ranked[-1]
            if furthest == "待确认工序" and len(ranked) > 1:
                return ranked[-2]
            if furthest == "待确认工序":
                return _LAST_MFG_PROCESS
            return furthest
        return normalize_process_name(latest_process) or _LAST_MFG_PROCESS
    return normalize_process_name(latest_process) or (ranked[-1] if ranked else STANDARD_PROCESSES[0])


def ensure_work_orders_from_ipqc(db: Session | None = None) -> dict:
    """按 IPQC 的 work_order_no 补齐工单；已存在则按检验实据整体刷新状态/工序/日期。"""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        today = date.today()
        now = datetime.now()

        insp_rows = (
            db.query(QualityInspectionRecord)
            .filter(
                QualityInspectionRecord.work_order_no.isnot(None),
                QualityInspectionRecord.work_order_no != "",
            )
            .all()
        )

        # work_order_no → 聚合画像
        buckets: dict[str, dict] = {}
        for row in insp_rows:
            order_no = (row.work_order_no or "").strip()
            if not order_no:
                continue
            b = buckets.get(order_no)
            if b is None:
                b = {
                    "min_at": None,
                    "max_at": None,
                    "insp_n": 0,
                    "qty_by_process": defaultdict(int),
                    "processes": set(),
                    "latest_process": None,
                    "product_code": None,
                    "material_name": None,
                    "customer_code": None,
                }
                buckets[order_no] = b

            at = row.inspected_at
            if at is not None:
                if b["min_at"] is None or at < b["min_at"]:
                    b["min_at"] = at
                if b["max_at"] is None or at > b["max_at"]:
                    b["max_at"] = at
                    b["latest_process"] = row.process_name

            process = normalize_process_name(row.process_name) or "待确认工序"
            b["processes"].add(process)
            qty = int(row.inspected_qty or 1)
            b["qty_by_process"][process] += max(qty, 1)
            b["insp_n"] += 1

            if not b["product_code"] and row.product_code:
                b["product_code"] = row.product_code
            if not b["material_name"] and row.material_name:
                b["material_name"] = row.material_name
            if not b["customer_code"] and row.customer_code:
                b["customer_code"] = row.customer_code

        existing = {
            wo.order_no: wo
            for wo in db.query(WorkOrder).filter(WorkOrder.order_no.in_(list(buckets))).all()
        } if buckets else {}

        created = 0
        updated = 0
        for order_no, b in buckets.items():
            min_at = b["min_at"]
            max_at = b["max_at"]
            min_d = min_at.date() if isinstance(min_at, datetime) else today
            max_d = max_at.date() if isinstance(max_at, datetime) else today
            status = _derive_status(min_d, max_d, today)
            process = _pick_current_process(
                status=status,
                latest_process=b["latest_process"],
                processes=b["processes"],
            )
            line = _PROCESS_LINE.get(process, "PCB产线")
            code = (b["product_code"] or "").strip() or None
            name = (b["material_name"] or "").strip()
            if not name:
                name = f"料号 {code[-10:]}" if code and len(code) > 10 else (code or "PCB 产品")

            # 计划量：各工序检验量峰值（同一批板跨工序重复计数时取峰值）
            plan_qty = max(int(v) for v in b["qty_by_process"].values()) if b["qty_by_process"] else int(b["insp_n"] or 1)
            plan_qty = max(plan_qty, 1)

            if status == "in_progress":
                # 在制：完成约 60%–85%，且未达计划量
                ratio = 0.6 + (sum(ord(ch) for ch in order_no) % 26) / 100.0
                actual = max(int(plan_qty * ratio), 1)
                if actual >= plan_qty:
                    actual = max(plan_qty - 1, 1)
                end_date = max_d + timedelta(days=2)
                actual_end = None
            else:
                actual = plan_qty
                end_date = max_d
                actual_end = (
                    max_at
                    if isinstance(max_at, datetime)
                    else datetime.combine(max_d, datetime.min.time())
                )

            priority = "high" if b["insp_n"] >= 8 else "normal"
            assignee = _stable_pick(order_no, _ASSIGNEES)
            remark = (
                f"IPQC 回填；客户 {b['customer_code'] or '-'}；"
                f"检验 {b['insp_n']} 笔；工序 {','.join(sorted(b['processes'], key=lambda p: _PROCESS_RANK.get(p, 99)))}"
            )[:500]
            actual_start = (
                min_at
                if isinstance(min_at, datetime)
                else datetime.combine(min_d, datetime.min.time())
            )

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
                    end_date=end_date,
                    actual_start_time=actual_start,
                    actual_end_time=actual_end,
                    current_process=process,
                    remark=remark,
                    created_at=actual_start,
                    updated_at=now,
                )
                db.add(wo)
                created += 1
            else:
                wo.product_name = name[:100]
                wo.product_code = code[:50] if code else wo.product_code
                wo.production_line = line
                wo.plan_quantity = plan_qty
                wo.actual_quantity = actual
                wo.status = status
                wo.priority = priority
                if not wo.assignee:
                    wo.assignee = assignee
                wo.start_date = min_d
                wo.end_date = end_date if status in ("completed", "closed") else end_date
                wo.actual_start_time = actual_start
                wo.actual_end_time = actual_end
                wo.current_process = process
                wo.remark = remark
                wo.updated_at = now
                updated += 1

        db.flush()

        # 回写检验记录 work_order_id（含曾挂到已删演示单的记录）
        wo_map = {
            order_no: wid
            for wid, order_no in db.query(WorkOrder.id, WorkOrder.order_no).all()
        }
        linked = 0
        for row in insp_rows:
            key = (row.work_order_no or "").strip()
            wid = wo_map.get(key)
            if wid and row.work_order_id != wid:
                row.work_order_id = wid
                linked += 1

        if own:
            db.commit()
        else:
            db.flush()

        return {
            "ipqc_orders": len(buckets),
            "created": created,
            "updated": updated,
            "linked_inspections": linked,
            "work_orders_total": db.query(WorkOrder).count(),
            "status_dist": dict(
                db.query(WorkOrder.status, func.count(WorkOrder.id))
                .group_by(WorkOrder.status)
                .all()
            ),
        }
    except Exception:
        if own:
            db.rollback()
        raise
    finally:
        if own:
            db.close()
