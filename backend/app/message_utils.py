"""消息中心等级工具 — 按消息类型映射高/中/低。"""

from __future__ import annotations

# 消息类型 -> 等级：业务告警=高，系统通知=中，公告通知=低
MESSAGE_LEVEL_BY_CATEGORY: dict[str, str] = {
    "alert": "high",
    "system": "medium",
    "announcement": "low",
}

CATEGORY_BY_MESSAGE_LEVEL: dict[str, str] = {
    level: category for category, level in MESSAGE_LEVEL_BY_CATEGORY.items()
}


def message_level_from_category(category: str) -> str:
    """根据消息类型返回等级（high / medium / low）。"""
    return MESSAGE_LEVEL_BY_CATEGORY.get(category, "medium")
