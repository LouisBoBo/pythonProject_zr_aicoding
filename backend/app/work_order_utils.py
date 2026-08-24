"""工单工序推导与在制数量计算（wip 口径）。"""

from __future__ import annotations

# 标准工序序列（与 quality_metrics / 种子数据一致）
STANDARD_PROCESSES: list[str] = ["贴片", "焊接", "AOI检测", "功能测试", "包装"]

# wip 口径：未完工且非取消
WIP_EXCLUDED_STATUSES: frozenset[str] = frozenset({"completed", "cancelled", "closed"})


def derive_current_process(
    status: str,
    plan_quantity: int,
    actual_quantity: int,
) -> str | None:
    """按工单状态与完成进度推导当前工序。待开工/已取消返回 None。"""
    if status in ("pending", "cancelled"):
        return None
    if status in ("completed", "closed"):
        return STANDARD_PROCESSES[-1]
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
