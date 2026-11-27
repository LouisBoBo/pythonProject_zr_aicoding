"""全系统统一工序 / 缺陷口径（与 IPQC 检验记录一致）。

品质看板、quality_metrics、工单当前工序、报工默认工序均引用本目录，
避免再出现「贴片/AOI」与「阻焊/钻孔」两套工序对不上的问题。
"""

from __future__ import annotations

# PCB / IPQC 主工序（流程顺序；待确认工序垫后）
STANDARD_PROCESSES: list[str] = ["钻孔", "蚀刻", "阻焊", "成型", "待确认工序"]

# 品质日汇总 / 看板默认工序（与 STANDARD 相同，显式别名便于阅读）
QUALITY_PROCESSES: list[str] = list(STANDARD_PROCESSES)

# IPQC 导入源工序 ID → 名称（与 ipqc_import 保持一致）
IPQC_PROCESS_NAME_MAP: dict[str, str] = {
    "3273661841000010": "成型",
    "3273661841000049": "钻孔",
    "3273661841000061": "阻焊",
    "3273661841000048": "待确认工序",
}

# 历史 SMT 演示口径 → IPQC 口径（迁移旧 metrics / 异常用）
LEGACY_PROCESS_ALIASES: dict[str, str] = {
    "贴片": "阻焊",
    "焊接": "蚀刻",
    "AOI检测": "钻孔",
    "AOI": "钻孔",
    "功能测试": "成型",
    "包装": "待确认工序",
    "组装": "成型",
    "检验": "待确认工序",
}

# 品质异常 / 缺陷类型（PCB）
QUALITY_DEFECT_TYPES: list[str] = [
    "阻焊擦花",
    "阻焊露铜",
    "孔偏",
    "孔破",
    "外形超差",
    "崩边",
    "线宽偏细",
    "侧蚀超标",
]

# metrics 无产线字段时的归集产线名
IPQC_METRICS_LINE = "PCB产线"


def normalize_process_name(name: str | None) -> str | None:
    """把任意工序名归一到标准目录；未知名称原样返回（去空白）。"""
    if name is None:
        return None
    text = str(name).strip()
    if not text:
        return None
    if text in STANDARD_PROCESSES:
        return text
    return LEGACY_PROCESS_ALIASES.get(text, text)
