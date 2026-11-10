#!/usr/bin/env python3
"""每日对齐今日业务数据（幂等，可重复执行）。

供服务器 cron / systemd timer 在每天 08:00 调用：
  补齐今日运营事实（产量/工时/库存相关）→ 可选重启 API。

用法（在 backend 目录或设置 PYTHONPATH）：
  python scripts/align_today_business_data.py
  python scripts/align_today_business_data.py --days 1
  python scripts/align_today_business_data.py --restart
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def align_today(*, days: int) -> None:
    from app.database import Base, engine
    from app.main import (
        ensure_employee_work_hours_recent_backfill,
        ensure_employee_work_hours_shift_type,
        ensure_equipment_repairs_repair_completed_at,
        ensure_equipment_runtime_logs_downtime_reason,
        ensure_inventory_stock_backfill,
        ensure_kanban_board_fields,
        ensure_maintenance_orders_plan_complete_date,
        ensure_material_inbound_backfill,
        ensure_material_purchase_fields,
        ensure_quality_anomaly_resolution_note,
        ensure_sales_orders_ordered_at,
        ensure_work_orders_actual_end_time,
        ensure_work_orders_actual_start_time,
        ensure_work_orders_current_process,
    )
    from app.seed_analytics import backfill_recent_operational_data, seed_analytics_data

    today = date.today()
    _log(f"开始对齐业务数据：today={today.isoformat()} days={days}")

    # 与 API lifespan 一致：先建表/补列，再回填今日数据
    _log("create_all + schema ensure…")
    Base.metadata.create_all(bind=engine)
    ensure_material_purchase_fields()
    ensure_sales_orders_ordered_at()
    ensure_kanban_board_fields()
    ensure_quality_anomaly_resolution_note()
    ensure_work_orders_actual_start_time()
    ensure_work_orders_actual_end_time()
    ensure_work_orders_current_process()
    ensure_maintenance_orders_plan_complete_date()
    ensure_equipment_repairs_repair_completed_at()
    ensure_employee_work_hours_shift_type()
    ensure_equipment_runtime_logs_downtime_reason()

    _log("seed_analytics_data（已有则跳过）…")
    seed_analytics_data()

    _log("ensure_employee_work_hours_recent_backfill…")
    ensure_employee_work_hours_recent_backfill()

    _log(f"backfill_recent_operational_data(days={days})…")
    backfill_recent_operational_data(days=days)

    _log("ensure_inventory_stock_backfill…")
    ensure_inventory_stock_backfill()

    _log("ensure_material_inbound_backfill…")
    ensure_material_inbound_backfill()

    _log("今日业务数据对齐完成")


def restart_api(service: str) -> None:
    _log(f"重启 API：systemctl restart {service}")
    subprocess.run(["systemctl", "restart", service], check=True)
    _log("API 已重启")


def main() -> int:
    parser = argparse.ArgumentParser(description="对齐今日业务数据")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="回填天数，默认 1（仅今日）；可按需加大",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="对齐完成后执行 systemctl restart（默认服务名 zr-aicoding-api）",
    )
    parser.add_argument(
        "--restart-service",
        default="zr-aicoding-api",
        help="systemd 服务名（配合 --restart）",
    )
    args = parser.parse_args()
    if args.days < 1:
        _log("错误：--days 须 >= 1")
        return 2

    try:
        align_today(days=args.days)
        if args.restart:
            restart_api(args.restart_service)
    except Exception as exc:  # noqa: BLE001 — 定时任务需完整落日志
        _log(f"失败：{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
