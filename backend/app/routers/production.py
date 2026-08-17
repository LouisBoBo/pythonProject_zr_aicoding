from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.models import User
from app.schemas import (
    CompletionChartPoint,
    ProductionDetailRow,
    ProductionOverviewResponse,
    ProductionOverviewStats,
    ProductionStatTrend,
)

router = APIRouter(prefix="/api/production", tags=["production"])

PRODUCTION_LINES = ["SMT-1线", "SMT-2线", "DIP线", "组装线", "测试线"]
WIP_STATUSES = ["待投料", "在制", "待检验", "待入库"]

LINE_PRODUCTS = {
    "SMT-1线": ["PCB-A100", "PCB-A200", "PCB-A300"],
    "SMT-2线": ["PCB-B100", "PCB-B200", "PCB-B300"],
    "DIP线": ["PCBA-C100", "PCBA-C200", "PCBA-C300"],
    "组装线": ["ASSY-D100", "ASSY-D200", "ASSY-D300"],
    "测试线": ["TEST-E100", "TEST-E200", "TEST-E300"],
}

LINE_DEVICES = {
    "SMT-1线": ["贴片机-01", "回流焊-01", "AOI检测-01", "收板机-01"],
    "SMT-2线": ["贴片机-02", "回流焊-02", "AOI检测-02", "收板机-02"],
    "DIP线": ["插件机-01", "波峰焊-01", "剪脚机-01", "ICT测试-01"],
    "组装线": ["装配工位-01", "锁螺丝机-01", "点胶机-01", "包装机-01"],
    "测试线": ["功能测试-01", "老化柜-01", "高压测试-01", "终检台-01"],
}

DEFECT_TYPES = ["外观不良", "尺寸偏差", "虚焊", "元件偏移", "功能异常", "其他"]


def _mock_production_overview() -> ProductionOverviewResponse:
    return ProductionOverviewResponse(
        achievement_rate=4,
        production_area=4,
        kpi_trends={
            "achievement_rate": ProductionStatTrend(direction="up", text="2.1%"),
            "production_area": ProductionStatTrend(direction="up", text="1.5%"),
        },
        stats=ProductionOverviewStats(
            today_completed=3720,
            today_area_output=11450.8,
            today_defect_total=25,
            daily_defect_rate="0.67%",
            today_incoming_boards=3800,
            trends={
                "achievement_rate": ProductionStatTrend(direction="up", text="2.1%"),
                "production_area": ProductionStatTrend(direction="up", text="1.8%"),
                "today_completed": ProductionStatTrend(direction="up", text="8.2%"),
                "today_area_output": ProductionStatTrend(direction="up", text="5.6%"),
                "today_defect_total": ProductionStatTrend(direction="down", text="12.0%"),
                "daily_defect_rate": ProductionStatTrend(direction="down", text="0.15%"),
                "today_incoming_boards": ProductionStatTrend(direction="up", text="3.1%"),
            },
        ),
        completion_chart=[
            CompletionChartPoint(label="08:00", lot_output=1200000, model_output=980000),
            CompletionChartPoint(label="10:00", lot_output=2800000, model_output=2100000),
            CompletionChartPoint(label="12:00", lot_output=4500000, model_output=3600000),
            CompletionChartPoint(label="14:00", lot_output=5200000, model_output=4100000),
        ],
        detail_rows=[
            ProductionDetailRow(
                time="08:46:12",
                process_card_no="PC-20260807-001",
                product_model="ZR-A100",
                quantity=500,
                today_completed=480,
                total_completed=480,
            ),
            ProductionDetailRow(
                time="08:46:28",
                process_card_no="PC-20260807-002",
                product_model="ZR-B200",
                quantity=800,
                today_completed=750,
                total_completed=750,
            ),
            ProductionDetailRow(
                time="08:46:35",
                process_card_no="PC-20260807-003",
                product_model="ZR-C300",
                quantity=600,
                today_completed=580,
                total_completed=580,
            ),
            ProductionDetailRow(
                time="08:46:41",
                process_card_no="PC-20260807-004",
                product_model="ZR-D400",
                quantity=400,
                today_completed=390,
                total_completed=390,
            ),
        ],
    )


@router.get("/overview", response_model=ProductionOverviewResponse)
def get_production_overview(_current_user: User = Depends(get_current_user)):
    return _mock_production_overview()


# ---------------------------------------------------------------------------
# 生产概览（重构版）：支持时间范围与产线联动，返回图表级 mock 数据
# ---------------------------------------------------------------------------

def _seed_of(text: str) -> int:
    value = 0
    for char in text:
        value = (value * 31 + ord(char)) & 0xFFFFFFFF
    return value


def _line_factor(line: str) -> float:
    if line == "全部":
        return 1.0
    idx = PRODUCTION_LINES.index(line) if line in PRODUCTION_LINES else 0
    return 0.96 + idx * 0.05


def _trend_labels_and_plan(period: str):
    if period == "day":
        labels = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]
        plan = [1200, 1200, 1200, 1200, 1200, 900, 600]
    elif period == "week":
        labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        plan = [10000, 10000, 10000, 10000, 10000, 6000, 2000]
    else:
        labels = ["第1周", "第2周", "第3周", "第4周"]
        plan = [45000, 45000, 45000, 42000]
    return labels, plan


def _output_trend(period: str, line: str) -> dict:
    labels, plan = _trend_labels_and_plan(period)
    factor = _line_factor(line)
    seed = _seed_of(line + period)
    actual = [
        round(p * factor * (0.93 + ((seed + i * 13) % 7) * 0.028))
        for i, p in enumerate(plan)
    ]
    return {
        "granularity": "day" if period == "month" else period,
        "labels": labels,
        "plan": plan,
        "actual": actual,
    }


def _achievement_comparison(line: str) -> list[dict]:
    if line == "全部":
        plans = [12800, 11600, 9800, 9200, 10600]
        items = []
        for idx, name in enumerate(PRODUCTION_LINES):
            plan = plans[idx]
            actual = round(plan * (0.9 + idx * 0.035))
            items.append(
                {
                    "name": name,
                    "plan_quantity": plan,
                    "actual_quantity": actual,
                    "achievement_rate": round(actual / plan * 100, 1),
                }
            )
        return items

    products = LINE_PRODUCTS.get(line, ["产品A", "产品B", "产品C"])
    base_plans = [5200, 4700, 4300]
    seed = _seed_of(line)
    items = []
    for idx, name in enumerate(products):
        plan = base_plans[idx]
        actual = round(plan * (0.9 + ((seed + idx * 29) % 7) * 0.032))
        items.append(
            {
                "name": name,
                "plan_quantity": plan,
                "actual_quantity": actual,
                "achievement_rate": round(actual / plan * 100, 1),
            }
        )
    return items


def _work_order_status(line: str) -> list[dict]:
    line_idx = PRODUCTION_LINES.index(line) if line in PRODUCTION_LINES else 0
    if line == "全部":
        counts = [12, 18, 64]
    else:
        counts = [3, 4 + (line_idx % 3), 14 + line_idx * 2]
    return [
        {"status": "待开工", "count": counts[0]},
        {"status": "进行中", "count": counts[1]},
        {"status": "完成", "count": counts[2]},
    ]


def _wip_overview(line: str) -> dict:
    if line == "全部":
        base = [
            [120, 360, 210, 150],
            [95, 310, 180, 120],
            [80, 280, 160, 110],
            [110, 250, 170, 130],
            [70, 220, 140, 90],
        ]
        rows = [
            {"name": PRODUCTION_LINES[i], "values": base[i]}
            for i in range(len(PRODUCTION_LINES))
        ]
    else:
        products = LINE_PRODUCTS.get(line, ["产品A", "产品B", "产品C"])
        seed = _seed_of(line + "wip")
        rows = []
        for idx, name in enumerate(products):
            base_values = [14 + idx * 6, 42 + idx * 9, 26 + idx * 5, 18 + idx * 4]
            factor = 0.9 + ((seed + idx * 11) % 5) * 0.05
            rows.append(
                {
                    "name": name,
                    "values": [max(1, round(v * factor)) for v in base_values],
                }
            )
    return {"statuses": WIP_STATUSES, "rows": rows}


def _line_load(line: str) -> list[dict]:
    if line == "全部":
        loads = [78, 86, 82, 74, 90]
        caps = [84, 89, 80, 76, 93]
        return [
            {
                "name": PRODUCTION_LINES[i],
                "load_rate": loads[i],
                "capacity_utilization": caps[i],
            }
            for i in range(len(PRODUCTION_LINES))
        ]

    devices = LINE_DEVICES.get(line, ["设备01", "设备02", "设备03", "设备04"])
    line_idx = PRODUCTION_LINES.index(line) if line in PRODUCTION_LINES else 0
    return [
        {
            "name": name,
            "load_rate": round(72 + line_idx * 2 + idx * 5, 1),
            "capacity_utilization": round(66 + line_idx * 3 + idx * 6, 1),
        }
        for idx, name in enumerate(devices)
    ]


def _quality(period: str, line: str) -> dict:
    line_idx = PRODUCTION_LINES.index(line) if line in PRODUCTION_LINES else 0
    labels, _ = _trend_labels_and_plan(period)
    if line == "全部":
        defect_rate = 2.34
    else:
        defect_rate = round(1.82 + line_idx * 0.38, 2)

    seed = _seed_of(line + period + "defect")
    trend = [
        {
            "label": label,
            "value": round(
                max(0.4, defect_rate + ((seed + i * 7) % 5 - 2) * 0.22), 2
            ),
        }
        for i, label in enumerate(labels)
    ]

    base_distribution = [38, 26, 21, 17, 11, 6]
    factor = 1.0 if line == "全部" else 0.7 + line_idx * 0.08
    distribution = [
        {"name": DEFECT_TYPES[i], "value": max(1, round(base_distribution[i] * factor))}
        for i in range(len(DEFECT_TYPES))
    ]
    return {
        "defect_rate": defect_rate,
        "defect_rate_trend": trend,
        "defect_distribution": distribution,
    }


def _equipment(line: str) -> list[dict]:
    if line == "全部":
        items = []
        for idx, name in enumerate(PRODUCTION_LINES):
            utilization = round(76 + idx * 3.2, 1)
            oee = round(62 + idx * 2.4, 1)
            items.append(
                {"name": name, "line_name": name, "utilization": utilization, "oee": oee}
            )
        return items

    devices = LINE_DEVICES.get(line, ["设备01", "设备02", "设备03", "设备04"])
    items = []
    for idx, name in enumerate(devices):
        utilization = round(70 + idx * 4, 1)
        oee = round(58 + idx * 3.2, 1)
        items.append(
            {"name": name, "line_name": line, "utilization": utilization, "oee": oee}
        )
    return items


def _mock_production_overview_v2(period: str, line: str) -> dict:
    comparison = _achievement_comparison(line)
    plan_quantity = sum(item["plan_quantity"] for item in comparison)
    actual_quantity = sum(item["actual_quantity"] for item in comparison)
    achievement_rate = round(actual_quantity / plan_quantity * 100, 1) if plan_quantity else 0

    trend = _output_trend(period, line)
    wip = _wip_overview(line)
    line_load = _line_load(line)

    plan_output = sum(trend["plan"])
    actual_output = sum(trend["actual"])
    completion_rate = round(actual_output / plan_output * 100, 1) if plan_output else 0
    wip_total = sum(sum(row["values"]) for row in wip["rows"])
    avg_line_load = (
        round(sum(item["load_rate"] for item in line_load) / len(line_load), 1)
        if line_load
        else 0
    )

    line_idx = PRODUCTION_LINES.index(line) if line in PRODUCTION_LINES else 0
    if line == "全部":
        today_output = 12860
        week_output = 82640
        in_progress_orders = 18
        completed_orders = 236
        pending_orders = 12
    else:
        today_output = round(2680 * (1 + line_idx * 0.12))
        week_output = round(16800 * (1 + line_idx * 0.12))
        in_progress_orders = 4 + line_idx
        completed_orders = 52 + line_idx * 7
        pending_orders = 3 + (line_idx % 3)

    return {
        "period": period,
        "production_line": line,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lines": PRODUCTION_LINES,
        "kpi": {
            "achievement_rate": achievement_rate,
            "plan_quantity": plan_quantity,
            "actual_quantity": actual_quantity,
            "achievement_diff": actual_quantity - plan_quantity,
            "today_output": today_output,
            "week_output": week_output,
            "in_progress_orders": in_progress_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "completion_rate": completion_rate,
            "completion_rate_trend": "+2.1%",
            "wip_total": wip_total,
            "wip_total_trend": "+3.4%",
            "avg_line_load": avg_line_load,
            "avg_line_load_trend": "-1.2%",
            "plan_achievement_rate": achievement_rate,
            "plan_achievement_rate_trend": "+1.6%",
        },
        "achievement_comparison": comparison,
        "output_trend": trend,
        "work_order_status": _work_order_status(line),
        "line_load": line_load,
        "wip_overview": wip,
        "quality": _quality(period, line),
        "equipment": _equipment(line),
    }


@router.get("/overview-v2")
def get_production_overview_v2(
    period: str = Query("day", pattern=r"^(day|week|month)$"),
    line: str = Query("全部"),
    _current_user: User = Depends(get_current_user),
):
    return _mock_production_overview_v2(period, line)
