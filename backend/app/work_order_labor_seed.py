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
        # 优先在制工单，其次近期完工，避免报工落到已删演示单或全是关闭单
        in_progress = (
            db.query(WorkOrder)
            .filter(WorkOrder.status == "in_progress")
            .order_by(WorkOrder.updated_at.desc())
            .limit(40)
            .all()
        )
        completed = (
            db.query(WorkOrder)
            .filter(WorkOrder.status.in_(("completed", "pending")))
            .order_by(WorkOrder.updated_at.desc())
            .limit(20)
            .all()
        )
        work_orders = list(in_progress) + [wo for wo in completed if wo not in in_progress]
        if not work_orders:
            work_orders = db.query(WorkOrder).order_by(WorkOrder.updated_at.desc()).limit(40).all()
        if not employees or not work_orders:
            return

        today = date.today()
        span = max(int(days), 1)

        # 清理挂空工单的孤儿报工
        valid_ids = [row[0] for row in db.query(WorkOrder.id).all()]
        if valid_ids:
            (
                db.query(WorkOrderLaborRecord)
                .filter(
                    (WorkOrderLaborRecord.work_order_id.is_(None))
                    | (~WorkOrderLaborRecord.work_order_id.in_(valid_ids))
                )
                .delete(synchronize_session=False)
            )
        else:
            db.query(WorkOrderLaborRecord).delete(synchronize_session=False)

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
                if process == "待确认工序":
                    process = _DEFAULT_PROCESSES[(emp_idx + day_offset) % max(len(_DEFAULT_PROCESSES) - 1, 1)]
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
