"""生产领料出库单 ORM（挂载在 work_orders 路由使用）。"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MaterialOutbound(Base):
    """物料出库单（生产领料出库）"""

    __tablename__ = "material_outbounds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    outbound_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    outbound_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="production_pick", index=True
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    material_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    material_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_no: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="件")
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    warehouse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    location_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outbound_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    picker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receiver_department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    material: Mapped["Material"] = relationship()  # type: ignore[name-defined]
    warehouse: Mapped["Warehouse"] = relationship()  # type: ignore[name-defined]
    location: Mapped["WarehouseLocation | None"] = relationship()  # type: ignore[name-defined]
