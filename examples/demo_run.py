"""Demonstration script for the top-level orchestrator."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Tuple

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.top_level import (  # noqa: E402  pylint: disable=wrong-import-position
    Checklist,
    FunctionSummary,
    LessonCard,
    TaskContext,
    TaskState,
    TopLevelOrchestrator,
)
from src.orchestrator.support import (  # noqa: E402  pylint: disable=wrong-import-position
    InMemoryKnowledgeService,
    InMemoryTaskRegistry,
    SimpleFeedbackRouter,
    build_default_gateway,
    build_gemini_gateway,
)


def build_demo_orchestrator(use_gemini: bool = False) -> Tuple[TopLevelOrchestrator, InMemoryTaskRegistry, InMemoryKnowledgeService]:
    """Construct an orchestrator wired with in-memory components."""

    registry = InMemoryTaskRegistry()
    knowledge = InMemoryKnowledgeService(
        function_index=[
            FunctionSummary(
                name="translate_and_spellcheck",
                description="翻译文本并执行拼写检查的组合函数",
                tags=["translation", "normalization"],
            ),
        ],
        lessons=[
            LessonCard(
                lesson_id="translation-001",
                title="翻译任务需先确认术语表",
                content="若用户未提供术语，需要主动询问或在输出中标记不确定项。",
            )
        ],
        checklists=[
            Checklist(
                name="default-review",
                items=[
                    "参数 schema 是否完整",
                    "是否提供验证方案",
                    "描述中是否说明副作用",
                ],
            )
        ],
    )

    gateway = build_gemini_gateway() if use_gemini else build_default_gateway()
    feedback = SimpleFeedbackRouter()
    orchestrator = TopLevelOrchestrator(registry, knowledge, gateway, feedback)
    return orchestrator, registry, knowledge


def display_context_summary(context: TaskContext) -> None:
    """Print a compact summary of the orchestration result."""

    print("== Orchestration Summary ==")
    print(f"Task ID     : {context.task_id}")
    print(f"Final State : {context.task_state.value}")

    print("\n-- Artifacts --")
    for key, value in context.artifacts.items():
        print(f"{key}:")
        print(_to_ascii(value))

    print("\n-- History --")
    for turn in context.history:
        print(f"[{turn.role}] {_to_ascii(turn.content)}")


def _to_ascii(value: object) -> str:
    """Return a console-friendly representation using ASCII escapes."""

    try:
        return json.dumps(value, ensure_ascii=True, indent=2, default=repr)
    except TypeError:
        return repr(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the orchestrator demo loop")
    parser.add_argument(
        "--use-gemini",
        action="store_true",
        help="Use Google Gemini via the GeminiAgentGateway (requires credentials)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    use_gemini = args.use_gemini or os.getenv("USE_GEMINI", "0") == "1"

    orchestrator, registry, knowledge = build_demo_orchestrator(use_gemini=use_gemini)

    if use_gemini:
        print("[info] Using GeminiAgentGateway — ensure GEMINI_API_KEY 或 Vertex 配置已就绪。")

    user_request = "请把产品描述翻译成英文，并顺便修正拼写错误"
    context = orchestrator.handle_new_task(user_request)

    display_context_summary(context)

    print("\n== Registry Snapshot ==")
    print(_to_ascii(registry.get(context.task_id)))

    print("\n== Knowledge Updates ==")
    updates = list(knowledge.committed_updates)
    if updates:
        for idx, update in enumerate(updates, start=1):
            print(f"Update #{idx}: {_to_ascii(update.as_dict() if hasattr(update, 'as_dict') else update)}")
    else:
        print("No knowledge updates")


if __name__ == "__main__":
    main()
