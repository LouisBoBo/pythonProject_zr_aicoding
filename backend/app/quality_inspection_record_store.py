"""品质检验记录 ORM（生产管理-品质管理模块）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, inspect, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base


class QualityInspectionRecord(Base):
    """品质检验记录"""

    __tablename__ = "quality_inspection_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    inspection_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    inspection_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # incoming / process / final
    inspection_result: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # pass / fail / conditional
    work_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_orders.id"), nullable=True, index=True
    )
    work_order_no: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    batch_no: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    material_id: Mapped[int | None] = mapped_column(
        ForeignKey("materials.id"), nullable=True, index=True
    )
    material_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    material_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    inspector: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    non_conforming_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )


def ensure_quality_inspection_records_schema(bind_engine) -> None:
    """确保 quality_inspection_records 表存在（兼容已有 SQLite 库）。"""
    inspector = inspect(bind_engine)
    if inspector.has_table("quality_inspection_records"):
        return
    QualityInspectionRecord.__table__.create(bind=bind_engine, checkfirst=True)


def seed_quality_inspection_records(db: Session) -> None:
    """写入演示检验记录（表为空时执行）。"""
    if db.query(QualityInspectionRecord).first():
        return

    from app.models import Material, WorkOrder

    work_orders = db.query(WorkOrder).order_by(WorkOrder.id).limit(3).all()
    materials = db.query(Material).order_by(Material.id).limit(3).all()
    now = datetime.utcnow()
    today = date.today()

    def _wo(idx: int):
        return work_orders[idx] if idx < len(work_orders) else None

    def _mat(idx: int):
        return materials[idx] if idx < len(materials) else None

    samples = [
        {
            "inspection_no": f"QC-{today:%Y%m%d}-001",
            "inspection_type": "incoming",
            "inspection_result": "pass",
            "inspector": "周八",
            "inspected_at": now - timedelta(hours=2),
            "non_conforming_qty": 0,
            "remark": "来料外观与规格符合要求",
            "batch_no": "BATCH-20250901-A",
            "wo_idx": 0,
            "mat_idx": 0,
        },
        {
            "inspection_no": f"QC-{today:%Y%m%d}-002",
            "inspection_type": "process",
            "inspection_result": "fail",
            "inspector": "张工",
            "inspected_at": now - timedelta(hours=5),
            "non_conforming_qty": 12,
            "remark": "焊接工序虚焊超标，已通知产线复检",
            "batch_no": "BATCH-20250901-B",
            "wo_idx": 1,
            "mat_idx": 1,
        },
        {
            "inspection_no": f"QC-{today:%Y%m%d}-003",
            "inspection_type": "process",
            "inspection_result": "conditional",
            "inspector": "李工",
            "inspected_at": now - timedelta(days=1, hours=3),
            "non_conforming_qty": 3,
            "remark": "AOI 检出轻微偏移，让步接收",
            "batch_no": "BATCH-20250831-C",
            "wo_idx": 1,
            "mat_idx": 1,
        },
        {
            "inspection_no": f"QC-{(today - timedelta(days=1)):%Y%m%d}-001",
            "inspection_type": "final",
            "inspection_result": "pass",
            "inspector": "王检验",
            "inspected_at": now - timedelta(days=1, hours=8),
            "non_conforming_qty": 0,
            "remark": "出货检验合格",
            "batch_no": "BATCH-20250831-D",
            "wo_idx": 2,
            "mat_idx": 2,
        },
        {
            "inspection_no": f"QC-{(today - timedelta(days=2)):%Y%m%d}-001",
            "inspection_type": "final",
            "inspection_result": "fail",
            "inspector": "赵质检",
            "inspected_at": now - timedelta(days=2, hours=4),
            "non_conforming_qty": 8,
            "remark": "功能测试不合格，已隔离待返工",
            "batch_no": "BATCH-20250830-E",
            "wo_idx": 0,
            "mat_idx": 0,
        },
    ]

    for item in samples:
        wo = _wo(item["wo_idx"])
        mat = _mat(item["mat_idx"])
        db.add(
            QualityInspectionRecord(
                inspection_no=item["inspection_no"],
                inspection_type=item["inspection_type"],
                inspection_result=item["inspection_result"],
                work_order_id=wo.id if wo else None,
                work_order_no=wo.order_no if wo else None,
                batch_no=item["batch_no"],
                material_id=mat.id if mat else None,
                material_code=mat.material_code if mat else None,
                material_name=mat.material_name if mat else None,
                inspector=item["inspector"],
                inspected_at=item["inspected_at"],
                non_conforming_qty=item["non_conforming_qty"],
                remark=item["remark"],
            )
        )
    db.commit()
