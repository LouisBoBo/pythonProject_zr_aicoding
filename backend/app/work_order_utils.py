"""工单工序推导与在制数量计算（wip 口径）。"""

from __future__ import annotations

from datetime import datetime

# 标准工序序列（与 quality_metrics / 种子数据一致）
STANDARD_PROCESSES: list[str] = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]

# wip 口径：未完工且非取消
WIP_EXCLUDED_STATUSES: frozenset[str] = frozenset({"completed", "cancelled", "closed"})
FINISHED_STATUSES: frozenset[str] = frozenset({"completed", "closed"})


def derive_current_process(
    status: str,
    plan_quantity: int,
    actual_quantity: int,
) -> str:
    """按工单状态与完成进度推导当前工序。任意状态均返回非空工序。"""
    if status == "pending":
        return STANDARD_PROCESSES[0]
    if status in FINISHED_STATUSES:
        return STANDARD_PROCESSES[-1]
    if status == "cancelled":
        if plan_quantity > 0 and actual_quantity > 0:
            ratio = actual_quantity / plan_quantity
            step = min(int(ratio * len(STANDARD_PROCESSES)), len(STANDARD_PROCESSES) - 1)
            return STANDARD_PROCESSES[step]
        return STANDARD_PROCESSES[0]
    # in_progress 及其他
    if plan_quantity <= 0:
        return STANDARD_PROCESSES[0]
    ratio = actual_quantity / plan_quantity
    step = min(int(ratio * len(STANDARD_PROCESSES)), len(STANDARD_PROCESSES) - 1)
    return STANDARD_PROCESSES[step]


def calc_wip_quantity(plan_quantity: int, actual_quantity: int) -> int:
    """在制数量 = max(计划 - 实际, 0)。"""
    return max(plan_quantity - actual_quantity, 0)


def is_wip_status(status: str) -> bool:
    """是否在制品口径内（未完工且非取消）。"""
    return status not in WIP_EXCLUDED_STATUSES


def ensure_work_order_timestamps(work_order, *, now: datetime | None = None) -> None:
    """按状态补齐实际开始/结束时间：完工/关闭必须有实际结束时间。"""
    now = now or datetime.utcnow()
    status = work_order.status
    if status == "in_progress" and work_order.actual_start_time is None:
        work_order.actual_start_time = now
    if status in FINISHED_STATUSES:
        if work_order.actual_end_time is None:
            work_order.actual_end_time = now
        if work_order.actual_start_time is None:
            work_order.actual_start_time = work_order.actual_end_time or now
