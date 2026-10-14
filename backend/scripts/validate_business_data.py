"""只读校验：演示库业务数据逻辑与生产场景合理性。"""
from __future__ import annotations

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import (
    EmployeeWorkHour,
    EquipmentOeeSnapshot,
    EquipmentRepair,
    InventoryBalance,
    InventoryStock,
    ProductionLine,
    ProductionOutputRecord,
    ProductionPlan,
    Product,
    QualityMetrics,
    SalesOrder,
    WorkOrder,
)


def _pct_ok(v: float | Decimal | None) -> bool:
    if v is None:
        return False
    return 0 <= float(v) <= 100


def main() -> None:
    today = date.today()
    issues: list[dict] = []
    warnings: list[dict] = []
    ok: list[str] = []

    db = SessionLocal()
    try:
        counts = {
            "lines": db.query(ProductionLine).count(),
            "products": db.query(Product).count(),
            "work_orders": db.query(WorkOrder).count(),
            "output_records": db.query(ProductionOutputRecord).count(),
            "plans": db.query(ProductionPlan).count(),
        }
        print("=== 数据规模 ===")
        for k, v in counts.items():
            print(f"  {k}: {v}")

        bad_dates = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.start_date.isnot(None),
                WorkOrder.end_date.isnot(None),
                WorkOrder.end_date < WorkOrder.start_date,
            )
            .count()
        )
        if bad_dates:
            issues.append({"area": "工单", "rule": "计划结束日 >= 计划开始日", "count": bad_dates})
        else:
            ok.append("工单计划日期区间合法")

        actual_time_inverted = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.actual_start_time.isnot(None),
                WorkOrder.actual_end_time.isnot(None),
                WorkOrder.actual_end_time < WorkOrder.actual_start_time,
            )
            .count()
        )
        if actual_time_inverted:
            issues.append(
                {
                    "area": "工单",
                    "rule": "实际结束时间 >= 实际开始时间",
                    "count": actual_time_inverted,
                }
            )
        else:
            ok.append("工单实际开工/完工时间顺序正确")

        pending_past_end = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.end_date.isnot(None),
                WorkOrder.end_date < today,
                WorkOrder.status.notin_(["completed", "cancelled"]),
            )
            .count()
        )
        ok.append(f"逾期未完工单 {pending_past_end} 张（逾期预警演示）")

        completed_over = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.status == "completed",
                WorkOrder.actual_quantity > WorkOrder.plan_quantity * 1.15,
            )
            .count()
        )
        if completed_over:
            warnings.append(
                {"area": "工单", "rule": "已完成超产 >15%", "count": completed_over}
            )

        plan_rows = (
            db.query(
                ProductionPlan.plan_date,
                ProductionPlan.production_line_id,
                ProductionPlan.product_id,
                func.sum(ProductionPlan.plan_qty).label("plan_qty"),
            )
            .filter(ProductionPlan.plan_date >= date(today.year, today.month, 1))
            .group_by(
                ProductionPlan.plan_date,
                ProductionPlan.production_line_id,
                ProductionPlan.product_id,
            )
            .all()
        )
        mismatch_days = 0
        for row in plan_rows:
            day_start = datetime.combine(row.plan_date, datetime.min.time())
            day_end = datetime.combine(row.plan_date, datetime.max.time())
            actual_sum = (
                db.query(func.coalesce(func.sum(ProductionOutputRecord.actual_qty), 0))
                .filter(
                    ProductionOutputRecord.production_line_id == row.production_line_id,
                    ProductionOutputRecord.product_id == row.product_id,
                    ProductionOutputRecord.record_at >= day_start,
                    ProductionOutputRecord.record_at <= day_end,
                )
                .scalar()
            )
            plan_qty = int(row.plan_qty or 0)
            if plan_qty <= 0:
                continue
            ratio = int(actual_sum) / plan_qty
            if row.plan_date == today:
                if ratio < 0.05 or ratio > 1.5:
                    mismatch_days += 1
            elif ratio < 0.5 or ratio > 1.2:
                mismatch_days += 1
        if mismatch_days:
            warnings.append(
                {
                    "area": "生产计划/产量",
                    "rule": "日实际相对计划偏离过大",
                    "count": mismatch_days,
                    "note": "当日按小时累计、历史日 88–97% 为种子设计",
                }
            )
        else:
            ok.append("当月日产量与计划量整体在合理达成率区间")

        q_bad = 0
        for qm in db.query(QualityMetrics).all():
            total = qm.total_inspected or 0
            parts = (qm.good_count or 0) + (qm.defect_count or 0) + (qm.scrap_count or 0)
            if total > 0 and parts != total:
                q_bad += 1
        if q_bad:
            issues.append({"area": "品质", "rule": "良品+不良+报废=检验总数", "count": q_bad})
        else:
            ok.append("品质日汇总数量勾稽正确")

        oee_bad = 0
        for snap in db.query(EquipmentOeeSnapshot).filter(
            EquipmentOeeSnapshot.period_type == "day"
        ):
            if not (
                _pct_ok(snap.availability)
                and _pct_ok(snap.performance)
                and _pct_ok(snap.quality)
            ):
                oee_bad += 1
                continue
            expected = round(
                float(snap.availability)
                * float(snap.performance)
                * float(snap.quality)
                / 10000,
                2,
            )
            if snap.oee is not None and abs(float(snap.oee) - expected) > 0.15:
                oee_bad += 1
        if oee_bad:
            issues.append({"area": "设备 OEE", "rule": "三率与 OEE 公式", "count": oee_bad})
        else:
            ok.append("设备 OEE 快照合理")

        neg_stock = db.query(InventoryBalance).filter(InventoryBalance.quantity < 0).count()
        if neg_stock:
            issues.append({"area": "库存余额", "rule": "数量非负", "count": neg_stock})
        else:
            ok.append("库存余额无负数")

        low_stock = (
            db.query(InventoryStock)
            .filter(
                InventoryStock.safety_stock > 0,
                InventoryStock.quantity < InventoryStock.safety_stock,
            )
            .count()
        )
        ok.append(f"低库存预警候选 {low_stock} 条")

        over_ship = (
            db.query(SalesOrder).filter(SalesOrder.shipped_qty > SalesOrder.plan_qty).count()
        )
        if over_ship:
            warnings.append({"area": "销售", "rule": "已发量>计划量", "count": over_ship})

        orphan_out = db.execute(
            text(
                """
                SELECT COUNT(*) FROM production_output_records r
                LEFT JOIN production_lines l ON l.id = r.production_line_id
                WHERE l.id IS NULL
                """
            )
        ).scalar()
        if orphan_out:
            issues.append({"area": "产量", "rule": "产线外键", "count": orphan_out})
        else:
            ok.append("产量记录外键完整")

        future_out = (
            db.query(ProductionOutputRecord)
            .filter(ProductionOutputRecord.record_at > datetime.now())
            .count()
        )
        if future_out:
            warnings.append({"area": "产量", "rule": "未来时间戳", "count": future_out})
        else:
            ok.append("产量无未来时间")

        bad_hours = (
            db.query(EmployeeWorkHour)
            .filter(
                (EmployeeWorkHour.work_hours < 0)
                | (EmployeeWorkHour.work_hours > 24)
                | (EmployeeWorkHour.overtime_hours < 0)
            )
            .count()
        )
        if bad_hours:
            issues.append({"area": "员工工时", "rule": "单日工时范围", "count": bad_hours})
        else:
            ok.append("员工工时取值合理")

        open_repairs = (
            db.query(EquipmentRepair)
            .filter(EquipmentRepair.status.in_(["pending", "in_progress"]))
            .count()
        )
        ok.append(f"未关闭维修单 {open_repairs} 条")

        max_out = db.query(func.max(ProductionOutputRecord.record_at)).scalar()
        max_q = db.query(func.max(QualityMetrics.record_date)).scalar()
        print("\n=== 时效 ===")
        print(f"  最新产量: {max_out}")
        print(f"  最新品质日: {max_q}")
        print(f"  今天: {today}")

        print("\n=== 通过 ===")
        for line in ok:
            print(f"  [OK] {line}")

        print("\n=== 警告 ===")
        if not warnings:
            print("  （无）")
        for w in warnings:
            extra = w.get("note", "")
            print(f"  [WARN] {w['area']}: {w['rule']} ({w.get('count', '')}) {extra}")

        print("\n=== 错误 ===")
        if not issues:
            print("  （无）")
        for i in issues:
            print(f"  [FAIL] {i['area']}: {i['rule']} — {i.get('count', '')} 条")

        print("\n=== 结论 ===")
        if issues:
            print("  存在硬逻辑错误，需修数据或种子逻辑。")
            sys.exit(1)
        if warnings:
            print("  核心勾稽正确；警告为演示边界（逾期、达成率波动），贴近 PCB/MES 演示场景。")
        else:
            print("  数据逻辑一致，符合演示型真实生产场景。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
