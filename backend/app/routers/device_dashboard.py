"""
设备看板 API — 设备运行监控与效能分析专用接口
"""

from datetime import date, datetime, timedelta
from random import Random

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.models import Equipment, EquipmentRepair, User
from app.schemas import (
    DeviceAlarmTrendResponse,
    DeviceDashboardListResponse,
    DeviceDashboardListItem,
    DeviceOEEResponse,
    DeviceOutputItem,
    DeviceOutputResponse,
    DeviceStatusSummaryResponse,
    DeviceStatusSummaryItem,
    DeviceUtilizationResponse,
)

router = APIRouter(prefix="/api/device", tags=["device-dashboard"])

_rng = Random(42)

# ---------- mock helpers ----------

def _mock_equipment_status() -> list[dict]:
    """模拟设备状态：基于 equipment 表记录推导状态摘要"""
    return [
        {"status": "运行", "count": 8, "color": "#52c41a"},
        {"status": "停机", "count": 2, "color": "#ff4d4f"},
        {"status": "待机", "count": 3, "color": "#faad14"},
        {"status": "维修", "count": 1, "color": "#fa8c16"},
    ]

def _mock_devices() -> list[dict]:
    return [
        {"code": "EQ-2024-001", "name": "1号CNC加工中心", "status": "运行", "runtime_hours": 128.5, "last_alarm": None},
        {"code": "EQ-2024-002", "name": "2号CNC加工中心", "status": "运行", "runtime_hours": 116.2, "last_alarm": "2026-08-05 14:22"},
        {"code": "EQ-2023-011", "name": "3号注塑机", "status": "运行", "runtime_hours": 95.0, "last_alarm": None},
        {"code": "EQ-2024-004", "name": "自动包装线", "status": "维修", "runtime_hours": 210.0, "last_alarm": "2026-08-07 08:10"},
        {"code": "EQ-2024-003", "name": "1号注塑机", "status": "停机", "runtime_hours": 350.1, "last_alarm": "2026-08-07 07:45"},
        {"code": "EQ-2024-005", "name": "精密磨床", "status": "运行", "runtime_hours": 80.3, "last_alarm": None},
        {"code": "EQ-2024-006", "name": "冲压机A", "status": "待机", "runtime_hours": 200.0, "last_alarm": "2026-08-06 11:30"},
        {"code": "EQ-2024-007", "name": "激光切割机", "status": "运行", "runtime_hours": 142.7, "last_alarm": None},
        {"code": "EQ-2024-008", "name": "折弯机B", "status": "待机", "runtime_hours": 88.4, "last_alarm": None},
        {"code": "EQ-2024-009", "name": "焊机工作站1", "status": "运行", "runtime_hours": 167.9, "last_alarm": "2026-08-07 01:15"},
        {"code": "EQ-2024-010", "name": "焊机工作站2", "status": "运行", "runtime_hours": 154.2, "last_alarm": None},
        {"code": "EQ-2024-013", "name": "铣床X1", "status": "待机", "runtime_hours": 35.0, "last_alarm": None},
        {"code": "EQ-2024-012", "name": "喷涂机器人", "status": "运行", "runtime_hours": 210.5, "last_alarm": None},
        {"code": "EQ-2023-015", "name": "老旧铣床", "status": "停机", "runtime_hours": 999.9, "last_alarm": "2026-08-06 18:00"},
    ]


# ---------- summary ----------

@router.get("/status/summary", response_model=DeviceStatusSummaryResponse)
def device_status_summary(_current_user: User = Depends(get_current_user)):
    items = _mock_equipment_status()
    total = sum(i["count"] for i in items)
    return DeviceStatusSummaryResponse(
        items=[
            DeviceStatusSummaryItem(
                status=i["status"],
                count=i["count"],
                percent=round(i["count"] / total * 100, 1),
                color=i["color"],
            )
            for i in items
        ],
        total=total,
    )


# ---------- OEE ----------

@router.get("/oee", response_model=DeviceOEEResponse)
def device_oee(_current_user: User = Depends(get_current_user)):
    return DeviceOEEResponse(
        availability=87.2,
        performance=82.5,
        quality=95.8,
        oee=68.9,
    )


# ---------- list ----------

@router.get("/list", response_model=DeviceDashboardListResponse)
def device_dashboard_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    _current_user: User = Depends(get_current_user),
):
    all_devices = _mock_devices()
    if status and status != "全部":
        all_devices = [d for d in all_devices if d["status"] == status]
    total = len(all_devices)
    start = (page - 1) * page_size
    chunk = all_devices[start : start + page_size]
    return DeviceDashboardListResponse(
        items=[
            DeviceDashboardListItem(
                code=d["code"],
                name=d["name"],
                status=d["status"],
                runtime_hours=d["runtime_hours"],
                last_alarm=d["last_alarm"],
            )
            for d in chunk
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------- utilization ----------

@router.get("/utilization", response_model=DeviceUtilizationResponse)
def device_utilization(
    period: str = Query("day", pattern=r"^(day|week|month)$"),
    _current_user: User = Depends(get_current_user),
):
    today = date.today()
    if period == "day":
        labels = [f"{h:02d}:00" for h in range(8, 21)]
        values = [round(60 + _rng.uniform(0, 35), 1) for _ in labels]
    elif period == "week":
        labels = [(today - timedelta(days=i)).strftime("%m/%d") for i in range(6, -1, -1)]
        values = [round(55 + _rng.uniform(0, 40), 1) for _ in labels]
    else:
        labels = [f"W{i}" for i in range(1, 5)]
        values = [round(62 + _rng.uniform(0, 32), 1) for _ in labels]
    return DeviceUtilizationResponse(period=period, labels=labels, values=values)


# ---------- alarms trend ----------

@router.get("/alarms/trend", response_model=DeviceAlarmTrendResponse)
def device_alarms_trend(_current_user: User = Depends(get_current_user)):
    today = date.today()
    days = [(today - timedelta(days=i)).strftime("%m/%d") for i in range(9, -1, -1)]
    trend = [max(0, int(8 + _rng.gauss(0, 4))) for _ in days]
    type_items = [
        {"name": "电气故障", "value": 28},
        {"name": "机械故障", "value": 22},
        {"name": "液压故障", "value": 15},
        {"name": "控制系统", "value": 12},
        {"name": "传动故障", "value": 8},
        {"name": "其他", "value": 5},
    ]
    return DeviceAlarmTrendResponse(
        labels=days,
        values=trend,
        type_distribution=[{"name": t["name"], "value": t["value"]} for t in type_items],
    )


# ---------- output ----------

@router.get("/output", response_model=DeviceOutputResponse)
def device_output(_current_user: User = Depends(get_current_user)):
    items = [
        {"code": "EQ-2024-001", "name": "1号CNC加工中心", "today_output": 1250, "week_output": 8750},
        {"code": "EQ-2024-002", "name": "2号CNC加工中心", "today_output": 1180, "week_output": 8260},
        {"code": "EQ-2023-011", "name": "3号注塑机", "today_output": 960, "week_output": 6720},
        {"code": "EQ-2024-009", "name": "焊机工作站1", "today_output": 880, "week_output": 6160},
        {"code": "EQ-2024-010", "name": "焊机工作站2", "today_output": 810, "week_output": 5670},
        {"code": "EQ-2024-005", "name": "精密磨床", "today_output": 740, "week_output": 5180},
        {"code": "EQ-2024-007", "name": "激光切割机", "today_output": 690, "week_output": 4830},
        {"code": "EQ-2024-012", "name": "喷涂机器人", "today_output": 620, "week_output": 4340},
        {"code": "EQ-2024-006", "name": "冲压机A", "today_output": 450, "week_output": 3150},
        {"code": "EQ-2024-008", "name": "折弯机B", "today_output": 320, "week_output": 2240},
    ]
    return DeviceOutputResponse(
        items=[DeviceOutputItem(**i) for i in items],
    )
