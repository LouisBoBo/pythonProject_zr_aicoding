"""关联与严重业务约束复检（只读）。"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models import ProductionOutputRecord, ProductionPlan


def main() -> None:
    db = SessionLocal()
    fails: list[str] = []
    ok: list[str] = []
    mild: list[str] = []

    def q(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    checks = [
        (
            "产量-产线孤儿",
            "SELECT COUNT(*) FROM production_output_records r "
            "LEFT JOIN production_lines l ON l.id=r.production_line_id WHERE l.id IS NULL",
        ),
        (
            "产量-产品孤儿",
            "SELECT COUNT(*) FROM production_output_records r "
            "LEFT JOIN products p ON p.id=r.product_id "
            "WHERE r.product_id IS NOT NULL AND p.id IS NULL",
        ),
        (
            "产量-工单孤儿",
            "SELECT COUNT(*) FROM production_output_records r "
            "LEFT JOIN work_orders w ON w.id=r.work_order_id "
            "WHERE r.work_order_id IS NOT NULL AND w.id IS NULL",
        ),
        (
            "计划-产线孤儿",
            "SELECT COUNT(*) FROM production_plans p "
            "LEFT JOIN production_lines l ON l.id=p.production_line_id WHERE l.id IS NULL",
        ),
        (
            "计划-产品孤儿",
            "SELECT COUNT(*) FROM production_plans p "
            "LEFT JOIN products pr ON pr.id=p.product_id WHERE pr.id IS NULL",
        ),
        (
            "发货-订单孤儿",
            "SELECT COUNT(*) FROM shipment_records s "
            "LEFT JOIN sales_orders o ON o.id=s.sales_order_id WHERE o.id IS NULL",
        ),
        (
            "库存余额-物料孤儿",
            "SELECT COUNT(*) FROM inventory_balances b "
            "LEFT JOIN materials m ON m.id=b.material_id WHERE m.id IS NULL",
        ),
        (
            "库存流水-物料孤儿",
            "SELECT COUNT(*) FROM inventory_transactions t "
            "LEFT JOIN materials m ON m.id=t.material_id WHERE m.id IS NULL",
        ),
        (
            "保养工单-设备孤儿",
            "SELECT COUNT(*) FROM equipment_maintenance_orders mo "
            "LEFT JOIN equipment e ON e.id=mo.equipment_id WHERE e.id IS NULL",
        ),
        (
            "维修-设备孤儿",
            "SELECT COUNT(*) FROM equipment_repairs r "
            "LEFT JOIN equipment e ON e.id=r.equipment_id WHERE e.id IS NULL",
        ),
        (
            "工单计划日期倒挂",
            "SELECT COUNT(*) FROM work_orders WHERE end_date IS NOT NULL "
            "AND start_date IS NOT NULL AND end_date < start_date",
        ),
        (
            "工单实际时间倒挂",
            "SELECT COUNT(*) FROM work_orders WHERE actual_start_time IS NOT NULL "
            "AND actual_end_time IS NOT NULL AND actual_end_time < actual_start_time",
        ),
        (
            "完成工单负产量",
            "SELECT COUNT(*) FROM work_orders WHERE status='completed' AND actual_quantity < 0",
        ),
        ("销售超发", "SELECT COUNT(*) FROM sales_orders WHERE shipped_qty > plan_qty"),
        ("库存余额负数", "SELECT COUNT(*) FROM inventory_balances WHERE quantity < 0"),
        ("汇总库存负数", "SELECT COUNT(*) FROM inventory_stock WHERE quantity < 0"),
        (
            "品质数量不勾稽",
            "SELECT COUNT(*) FROM quality_metrics WHERE total_inspected > 0 "
            "AND (good_count + defect_count + scrap_count) != total_inspected",
        ),
        (
            "员工无工号",
            "SELECT COUNT(*) FROM employees WHERE employee_no IS NULL OR trim(employee_no) = ''",
        ),
        (
            "订单已发与发货明细不一致",
            """SELECT COUNT(*) FROM (
              SELECT o.id FROM sales_orders o
              LEFT JOIN (
                SELECT sales_order_id, SUM(ship_qty) AS s
                FROM shipment_records GROUP BY sales_order_id
              ) x ON x.sales_order_id = o.id
              WHERE COALESCE(x.s, 0) != o.shipped_qty
            )""",
        ),
    ]

    print("=== 关联与严重业务检查 ===")
    for label, sql in checks:
        n = q(sql)
        if n == 0:
            ok.append(label)
            print(f"  [OK] {label}")
        else:
            fails.append(f"{label} ({n})")
            print(f"  [FAIL] {label}: {n}")

    today = date.today()
    bad_severe = 0
    rows = (
        db.query(
            ProductionPlan.plan_date,
            ProductionPlan.production_line_id,
            ProductionPlan.product_id,
            func.sum(ProductionPlan.plan_qty),
        )
        .filter(ProductionPlan.plan_date >= date(today.year, today.month, 1))
        .group_by(
            ProductionPlan.plan_date,
            ProductionPlan.production_line_id,
            ProductionPlan.product_id,
        )
        .all()
    )
    for row in rows:
        d = row[0]
        if d == today:
            continue
        t0 = datetime.combine(d, datetime.min.time())
        t1 = datetime.combine(d, datetime.max.time())
        actual = (
            db.query(func.sum(ProductionOutputRecord.actual_qty))
            .filter(
                ProductionOutputRecord.production_line_id == row[1],
                ProductionOutputRecord.product_id == row[2],
                ProductionOutputRecord.record_at >= t0,
                ProductionOutputRecord.record_at <= t1,
            )
            .scalar()
            or 0
        )
        plan = int(row[3] or 0)
        if plan <= 0:
            continue
        ratio = int(actual) / plan
        if ratio > 1.5 or ratio < 0.4:
            bad_severe += 1

    if bad_severe:
        mild.append(f"历史日产量严重偏离计划 (>150% 或 <40%): {bad_severe} 组")
        print(f"  [MILD] 历史日产量严重偏离: {bad_severe} 组")
    else:
        print("  [OK] 历史日产量与计划无严重偏离")

    future = q(
        "SELECT COUNT(*) FROM production_output_records WHERE record_at > datetime('now', 'localtime')"
    )
    if future:
        mild.append(f"未来时刻产量: {future} 条")
        print(f"  [MILD] 未来时刻产量: {future} 条（当日班次演示）")
    else:
        print("  [OK] 无未来产量时间")

    print("\n=== 结论 ===")
    if fails:
        print(f"  发现 {len(fails)} 项严重问题: " + "; ".join(fails))
        sys.exit(1)
    print("  未发现严重业务关联错误（外键、勾稽、负库存、超发、时间倒挂等均为 0）。")
    if mild:
        print("  轻度提示: " + "; ".join(mild))
    db.close()


if __name__ == "__main__":
    main()
