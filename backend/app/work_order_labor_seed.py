"""工单报工明细（work_order_labor_records）种子数据。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.database import SessionLocal
from app.models import Employee, WorkOrder, WorkOrderLaborRecord

_DEFAULT_PROCESSES = ("贴片", "焊接", "组装", "检验", "包装")


def ensure_work_order_labor_records() -> None:
    """若报工明细为空，则按在职员工与现有工单生成近 7 日演示数据。"""
    db = SessionLocal()
    try:
        if db.query(WorkOrderLaborRecord.id).first():
            return

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
        rows: list[WorkOrderLaborRecord] = []
        for day_offset in range(7):
            work_date = today - timedelta(days=day_offset)
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

        db.add_all(rows)
        db.commit()
    finally:
        db.close()
