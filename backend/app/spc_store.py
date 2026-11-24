"""SPC 控制图：图表配置、测量点与控制限计算。"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from statistics import mean, stdev

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base

# X̄-R 图常数（子组大小 n）
_A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
_D3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
_D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
# I-MR 图：个体图控制限系数（基于 MR 的 d2≈1.128，E2=3/d2≈2.66）
_E2_IMR = 2.66
_D3_IMR = 0.0
_D4_IMR = 3.267


class SpcChart(Base):
    """SPC 控制图配置与最近一次计算结果。"""

    __tablename__ = "spc_charts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chart_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    chart_name: Mapped[str] = mapped_column(String(100), nullable=False)
    process_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    characteristic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chart_type: Mapped[str] = mapped_column(String(20), nullable=False, default="I-MR")  # I-MR / Xbar-R
    subgroup_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    usl: Mapped[float | None] = mapped_column(Float, nullable=True)
    lsl: Mapped[float | None] = mapped_column(Float, nullable=True)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 最近计算结果（JSON）
    data_points: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    ucl: Mapped[float | None] = mapped_column(Float, nullable=True)
    cl: Mapped[float | None] = mapped_column(Float, nullable=True)
    lcl: Mapped[float | None] = mapped_column(Float, nullable=True)
    cp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpk: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")  # normal / alert
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class SpcMeasurement(Base):
    """SPC 原始测量值。"""

    __tablename__ = "spc_measurements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chart_id: Mapped[int] = mapped_column(ForeignKey("spc_charts.id"), nullable=False, index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    subgroup_index: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    sample_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


def ensure_spc_schema(bind_engine) -> None:
    """确保 SPC 表存在（表在、接口此前未交付）。"""
    inspector = inspect(bind_engine)
    if not inspector.has_table("spc_charts"):
        SpcChart.__table__.create(bind=bind_engine, checkfirst=True)
    if not inspector.has_table("spc_measurements"):
        SpcMeasurement.__table__.create(bind=bind_engine, checkfirst=True)


def _safe_stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(stdev(values))


def compute_i_mr(values: list[float]) -> dict:
    """个体-移动极差（I-MR）控制限。"""
    if len(values) < 2:
        return {
            "points": [{"index": i + 1, "value": v, "out_of_control": False} for i, v in enumerate(values)],
            "ucl": None,
            "cl": None,
            "lcl": None,
            "mr_bar": None,
            "out_of_control_indexes": [],
        }
    mrs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar = mean(mrs) if mrs else 0.0
    cl = mean(values)
    ucl = cl + _E2_IMR * mr_bar
    lcl = cl - _E2_IMR * mr_bar
    out_idx: list[int] = []
    points = []
    for i, v in enumerate(values):
        ooc = v > ucl or v < lcl
        if ooc:
            out_idx.append(i + 1)
        points.append({"index": i + 1, "value": round(v, 4), "out_of_control": ooc})
    return {
        "points": points,
        "ucl": round(ucl, 4),
        "cl": round(cl, 4),
        "lcl": round(lcl, 4),
        "mr_bar": round(mr_bar, 4),
        "mr_ucl": round(_D4_IMR * mr_bar, 4),
        "mr_lcl": round(_D3_IMR * mr_bar, 4),
        "out_of_control_indexes": out_idx,
    }


def compute_xbar_r(values: list[float], subgroup_size: int) -> dict:
    """X̄-R 控制限。"""
    n = max(2, min(10, subgroup_size))
    subgroups: list[list[float]] = []
    for i in range(0, len(values) - len(values) % n, n):
        subgroups.append(values[i : i + n])
    if not subgroups:
        return compute_i_mr(values)

    xbars = [mean(g) for g in subgroups]
    ranges = [max(g) - min(g) for g in subgroups]
    xbar_bar = mean(xbars)
    r_bar = mean(ranges)
    a2 = _A2[n]
    ucl = xbar_bar + a2 * r_bar
    lcl = xbar_bar - a2 * r_bar
    out_idx: list[int] = []
    points = []
    for i, xb in enumerate(xbars):
        ooc = xb > ucl or xb < lcl
        if ooc:
            out_idx.append(i + 1)
        points.append(
            {
                "index": i + 1,
                "value": round(xb, 4),
                "range": round(ranges[i], 4),
                "out_of_control": ooc,
            }
        )
    return {
        "points": points,
        "ucl": round(ucl, 4),
        "cl": round(xbar_bar, 4),
        "lcl": round(lcl, 4),
        "r_bar": round(r_bar, 4),
        "r_ucl": round(_D4[n] * r_bar, 4),
        "r_lcl": round(_D3[n] * r_bar, 4),
        "subgroup_size": n,
        "out_of_control_indexes": out_idx,
    }


def compute_capability(values: list[float], usl: float | None, lsl: float | None) -> dict:
    """Cp / Cpk（样本标准差）。"""
    if len(values) < 2 or usl is None or lsl is None:
        return {"cp": None, "cpk": None, "mean": None, "stdev": None}
    if usl <= lsl:
        return {"cp": None, "cpk": None, "mean": None, "stdev": None}
    mu = mean(values)
    sigma = _safe_stdev(values)
    if sigma <= 0:
        return {"cp": None, "cpk": None, "mean": round(mu, 4), "stdev": 0.0}
    cp = (usl - lsl) / (6 * sigma)
    cpu = (usl - mu) / (3 * sigma)
    cpl = (mu - lsl) / (3 * sigma)
    cpk = min(cpu, cpl)
    return {
        "cp": round(cp, 3),
        "cpk": round(cpk, 3),
        "mean": round(mu, 4),
        "stdev": round(sigma, 4),
    }


def compute_chart(
    values: list[float],
    chart_type: str = "I-MR",
    subgroup_size: int = 1,
    usl: float | None = None,
    lsl: float | None = None,
) -> dict:
    """统一计算入口。"""
    if chart_type == "Xbar-R" and subgroup_size >= 2:
        limits = compute_xbar_r(values, subgroup_size)
    else:
        limits = compute_i_mr(values)
    cap = compute_capability(values, usl, lsl)
    status = "alert" if limits.get("out_of_control_indexes") else "normal"
    return {**limits, **cap, "status": status, "sample_count": len(values)}


def persist_chart_result(chart: SpcChart, result: dict) -> None:
    chart.data_points = json.dumps(result.get("points") or [], ensure_ascii=False)
    chart.ucl = result.get("ucl")
    chart.cl = result.get("cl")
    chart.lcl = result.get("lcl")
    chart.cp = result.get("cp")
    chart.cpk = result.get("cpk")
    chart.status = result.get("status") or "normal"
    chart.updated_at = datetime.utcnow()


def recompute_chart_from_measurements(db: Session, chart: SpcChart) -> dict:
    rows = (
        db.query(SpcMeasurement)
        .filter(SpcMeasurement.chart_id == chart.id)
        .order_by(SpcMeasurement.measured_at.asc(), SpcMeasurement.id.asc())
        .all()
    )
    values = [float(r.value) for r in rows]
    result = compute_chart(
        values,
        chart_type=chart.chart_type,
        subgroup_size=chart.subgroup_size,
        usl=chart.usl,
        lsl=chart.lsl,
    )
    # 附带测量时间轴
    if chart.chart_type != "Xbar-R" or chart.subgroup_size < 2:
        for i, pt in enumerate(result.get("points") or []):
            if i < len(rows):
                pt["measured_at"] = rows[i].measured_at.isoformat()
                pt["sample_label"] = rows[i].sample_label
    persist_chart_result(chart, result)
    db.commit()
    db.refresh(chart)
    return result


def seed_spc_data(db: Session) -> None:
    """写入演示 SPC 图与测量点（幂等）。"""
    if db.query(SpcChart).count() > 0:
        return

    charts_def = [
        {
            "chart_code": "SPC-DRILL-DIA",
            "chart_name": "钻孔孔径 I-MR",
            "process_name": "钻孔",
            "characteristic": "孔径",
            "chart_type": "I-MR",
            "subgroup_size": 1,
            "unit": "mm",
            "usl": 0.35,
            "lsl": 0.25,
            "target": 0.30,
            "center": 0.30,
            "sigma": 0.012,
            "n": 30,
        },
        {
            "chart_code": "SPC-LINE-WIDTH",
            "chart_name": "线路线宽 X̄-R",
            "process_name": "线路",
            "characteristic": "线宽",
            "chart_type": "Xbar-R",
            "subgroup_size": 5,
            "unit": "mm",
            "usl": 0.12,
            "lsl": 0.08,
            "target": 0.10,
            "center": 0.10,
            "sigma": 0.004,
            "n": 50,
        },
        {
            "chart_code": "SPC-SOLDER-THK",
            "chart_name": "阻焊膜厚 I-MR",
            "process_name": "阻焊",
            "characteristic": "膜厚",
            "chart_type": "I-MR",
            "subgroup_size": 1,
            "unit": "μm",
            "usl": 35.0,
            "lsl": 20.0,
            "target": 27.0,
            "center": 27.0,
            "sigma": 1.8,
            "n": 28,
        },
    ]

    rng = random.Random(42)
    now = datetime.utcnow()
    for cdef in charts_def:
        chart = SpcChart(
            chart_code=cdef["chart_code"],
            chart_name=cdef["chart_name"],
            process_name=cdef["process_name"],
            characteristic=cdef["characteristic"],
            chart_type=cdef["chart_type"],
            subgroup_size=cdef["subgroup_size"],
            unit=cdef["unit"],
            usl=cdef["usl"],
            lsl=cdef["lsl"],
            target=cdef["target"],
        )
        db.add(chart)
        db.flush()

        values: list[float] = []
        for i in range(cdef["n"]):
            v = rng.gauss(cdef["center"], cdef["sigma"])
            # 钻孔图末尾注入一个失控点，便于演示告警
            if cdef["chart_code"] == "SPC-DRILL-DIA" and i == cdef["n"] - 2:
                v = cdef["usl"] + 0.04
            values.append(round(v, 4))
            db.add(
                SpcMeasurement(
                    chart_id=chart.id,
                    measured_at=now - timedelta(hours=cdef["n"] - i),
                    value=values[-1],
                    subgroup_index=(i // cdef["subgroup_size"]) + 1,
                    sample_label=f"S{i + 1:03d}",
                )
            )

        result = compute_chart(
            values,
            chart_type=cdef["chart_type"],
            subgroup_size=cdef["subgroup_size"],
            usl=cdef["usl"],
            lsl=cdef["lsl"],
        )
        persist_chart_result(chart, result)

    db.commit()
