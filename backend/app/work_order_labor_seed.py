"""工单报工明细（work_order_labor_records）种子与近日补齐。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.database import SessionLocal
from app.models import Employee, WorkOrder, WorkOrderLaborRecord
from app.process_catalog import STANDARD_PROCESSES

_DEFAULT_PROCESSES = tuple(STANDARD_PROCESSES)


def ensure_work_order_labor_records(days: int = 7) -> None:
    """保证近 N 日有报工明细。

    - 表空：按在职员工 × 工单生成近 N 日演示数据
    - 已有：只补「缺日」的演示行（不覆盖已有 work_date）
    """
    db = SessionLocal()
    try:
        employees = (
            db.query(Employee)
            .filter(Employee.status == "在职")
            .order_by(Employee.employee_no)
            .all()
        )
        work_orders = db.query(WorkOrder).order_by(WorkOrder.id).limit(20).all()
        if not employees or not work_orders:
            return

        today = date.today()
        span = max(int(days), 1)
        existing_dates = {
            row[0]
            for row in db.query(WorkOrderLaborRecord.work_date)
            .filter(WorkOrderLaborRecord.work_date >= today - timedelta(days=span - 1))
            .distinct()
            .all()
        }

        rows: list[WorkOrderLaborRecord] = []
        for day_offset in range(span):
            work_date = today - timedelta(days=day_offset)
            if work_date in existing_dates:
                continue
            for emp_idx, emp in enumerate(employees):
                wo = work_orders[(emp_idx + day_offset) % len(work_orders)]
                process = (
                    (wo.current_process or "").strip()
                    or _DEFAULT_PROCESSES[(emp_idx + day_offset) % len(_DEFAULT_PROCESSES)]
                )
                hours = 6.0 + ((emp_idx + day_offset) % 5) * 0.5
                rows.append(
                    WorkOrderLaborRecord(
                        employee_no=emp.employee_no,
                        employee_name=emp.employee_name,
                        department_name=emp.department_name,
                        work_date=work_date,
                        work_order_id=wo.id,
                        process=process,
                        work_hours=hours,
                        created_at=datetime.utcnow(),
                    )
                )

        if rows:
            db.add_all(rows)
            db.commit()
    finally:
        db.close()
