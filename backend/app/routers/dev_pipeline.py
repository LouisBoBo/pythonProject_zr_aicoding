"""一体化 dev-pipeline 元数据（供 WorkBuddy / 编排器读取，避免误提示步骤 5 需用户确认）。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/dev-pipeline", tags=["一体化写码流程"])

_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_LINKED_RUN_NOTICE = (
    "任务已关联一体化写码流程（run_id={{run_id}}）。"
    "将依次执行：需求采集 → 需求理解 → 读库上下文 → 规划实现 → 写代码 → 验证 → 复核 → 提交。"
    "中间步骤自动执行，含写代码在内均无需您确认；请勿提示「步骤 5 会暂停等你确认」。"
)

_PIPELINE_PREFERENCES = {
    "begin_tool": "mes_dev_pipeline_begin",
    "coding_step_tool": "zr_cursor_begin",
    "report_data_tool": "zr_esc_mes_query",
    "report_chart_tool": "zr_esc_mcp_chart",
    "report_menu_anchor": "报表中心",
    "forbidden_tools": ["ask_user_question"],
    "report_chart_rules": [
        "表格正文紧贴插入 Markdown 图片 ![标题](url)，禁止裸链接",
        "单位不一致的计划/实际不画同一双轴图",
    ],
}

_STEPS = [
    {"index": 1, "name": "需求采集", "requires_user_confirmation": False},
    {"index": 2, "name": "需求理解", "requires_user_confirmation": False},
    {"index": 3, "name": "读库上下文", "requires_user_confirmation": False},
    {"index": 4, "name": "规划实现", "requires_user_confirmation": False},
    {"index": 5, "name": "写代码", "requires_user_confirmation": False},
    {"index": 6, "name": "验证", "requires_user_confirmation": False},
    {"index": 7, "name": "复核", "requires_user_confirmation": False},
    {"index": 8, "name": "提交", "requires_user_confirmation": False},
]


def _linked_run_notice_from_config() -> str:
    path = _PROJECT_ROOT / "config.yaml"
    if not path.is_file():
        return _LINKED_RUN_NOTICE
    text = path.read_text(encoding="utf-8")
    marker = "linked_run_user_notice: |"
    if marker not in text:
        return _LINKED_RUN_NOTICE
    block = text.split(marker, 1)[1]
    lines: list[str] = []
    for line in block.splitlines():
        if line and not line.startswith(" ") and not line.startswith("\t"):
            break
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines) if lines else _LINKED_RUN_NOTICE


@router.get(
    "/meta",
    summary="一体化写码流程说明",
    description=(
        "返回 8 步 dev-pipeline 定义及关联任务时的用户提示文案。"
        "步骤 5（写代码）requires_user_confirmation 恒为 false，中间流程不需用户确认。"
    ),
)
def dev_pipeline_meta(_: User = Depends(get_current_user)) -> dict:
    return {
        "integrated_coding_automatic": True,
        "step_5_requires_user_confirmation": False,
        "steps": _STEPS,
        "preferences": _PIPELINE_PREFERENCES,
        "linked_run_user_notice": _linked_run_notice_from_config(),
        "config_path": "config.yaml",
    }
