"""停机报表路由辅助函数单测。"""

from datetime import date, datetime, timedelta

from app.routers.equipment_downtime_report import (
    DOWNTIME_STATUS,
    _duration_hours,
    _normalize_downtime_date_range,
)
from app.models import EquipmentRuntimeLog


def test_normalize_downtime_date_range_swaps_when_inverted():
    d_from, d_to = _normalize_downtime_date_range(date(2026, 11, 10), date(2026, 11, 1))
    assert d_from == date(2026, 11, 1)
    assert d_to == date(2026, 11, 10)


def test_duration_hours_prefers_runtime_hours():
    log = EquipmentRuntimeLog(
        id=1,
        equipment_id=1,
        start_at=datetime(2026, 11, 1, 8, 0, 0),
        end_at=datetime(2026, 11, 1, 10, 0, 0),
        status=DOWNTIME_STATUS,
        runtime_hours=2.5,
    )
    assert _duration_hours(log) == 2.5


def test_duration_hours_from_interval_when_runtime_zero():
    start = datetime(2026, 11, 1, 8, 0, 0)
    end = start + timedelta(hours=1, minutes=30)
    log = EquipmentRuntimeLog(
        id=2,
        equipment_id=1,
        start_at=start,
        end_at=end,
        status=DOWNTIME_STATUS,
        runtime_hours=0,
    )
    assert _duration_hours(log) == 1.5