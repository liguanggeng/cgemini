"""Teaching-oriented Agent1 implementation.

This module exposes a lightweight handler that converts a payload from the
orchestrator into a structured task brief. It mirrors the prompt strategy
introduced in docs/agent1_design.md and is suitable for local demos.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.orchestrator.top_level import KnowledgeSnapshot


_DEFAULT_REQUIREMENTS = [
    "确认术语表或领域背景信息",
    "标注期望输出格式",
]

_DEFAULT_CONSTRAINTS = [
    "输出保持中文说明",
    "必要时引用函数索引",
]

_DEFAULT_OPEN_QUESTIONS = [
    "是否存在术语表或固定译法？",
]


def _extract_function_names(snapshot: KnowledgeSnapshot) -> List[str]:
    return [item.name for item in snapshot.function_index]


def _derive_lessons(snapshot: KnowledgeSnapshot) -> List[str]:
    return [card.title for card in snapshot.lessons]


def teaching_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a structured task brief for the orchestrator demo.

    Parameters
    ----------
    payload:
        Input dictionary containing user_request and knowledge (a
        KnowledgeSnapshot). Additional fields are ignored in this
        teaching variant.
    """

    snapshot = payload.get("knowledge") or KnowledgeSnapshot()

    reuse_candidates = _extract_function_names(snapshot)
    lessons_applied = _derive_lessons(snapshot)

    return {
        "objective": payload.get("user_request", ""),
        "requirements": list(_DEFAULT_REQUIREMENTS),
        "constraints": list(_DEFAULT_CONSTRAINTS),
        "tooling": {
            "reuse": reuse_candidates,
            "gaps": [] if reuse_candidates else ["需要新增函数来满足需求"],
            "notes": "按照函数参数要求准备输入，必要时更新工具索引。",
        },
        "open_questions": list(_DEFAULT_OPEN_QUESTIONS),
        "lessons_applied": lessons_applied,
        "lessons_to_add": [],
    }
