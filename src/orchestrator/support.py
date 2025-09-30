"""Support components for the top-level orchestrator.

This module provides in-memory implementations suitable for teaching and
local experimentation. They adhere to the protocols defined in
``top_level.py`` and are intentionally lightweight.
"""

from __future__ import annotations

import itertools
import os
from typing import Any, Callable, Dict, Iterable, List, Optional

from .gemini_gateway import GeminiAgentGateway
from .knowledge_store import KnowledgeStore
from .top_level import (
    AgentGatewayProtocol,
    Checklist,
    FeedbackRouterProtocol,
    FunctionSummary,
    KnowledgeServiceProtocol,
    KnowledgeSnapshot,
    KnowledgeUpdate,
    LessonCard,
    TaskContext,
    TaskRegistryProtocol,
    TaskState,
)


class InMemoryTaskRegistry(TaskRegistryProtocol):
    """Stores task metadata in memory for quick experiments."""

    _id_iter = itertools.count(1)

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def register(self, user_request: str) -> str:
        task_id = f"task-{next(self._id_iter)}"
        self._tasks[task_id] = {
            "request": user_request,
            "state": TaskState.PENDING,
        }
        return task_id

    def update_state(self, task_id: str, state: TaskState) -> None:
        self._tasks.setdefault(task_id, {})["state"] = state

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)


class InMemoryKnowledgeService(KnowledgeServiceProtocol):
    """Returns a pre-seeded knowledge snapshot and records updates."""

    def __init__(
        self,
        function_index: Optional[Iterable[FunctionSummary]] = None,
        lessons: Optional[Iterable[LessonCard]] = None,
        checklists: Optional[Iterable[Checklist]] = None,
        *,
        store_path: Optional[os.PathLike[str] | str] = "data/knowledge_updates.jsonl",
    ) -> None:
        self._snapshot = KnowledgeSnapshot(
            function_index=list(function_index or []),
            lessons=list(lessons or []),
            audit_checklists=list(checklists or []),
        )
        self._pending_updates: List[KnowledgeUpdate] = []
        self._store = KnowledgeStore(store_path) if store_path else None

    def load_snapshot(self) -> KnowledgeSnapshot:
        return self._snapshot

    def commit_updates(self, updates: Iterable[KnowledgeUpdate]) -> None:
        normalized = [TaskContext._coerce_knowledge_update(update) for update in updates if update]
        if not normalized:
            return
        self._pending_updates.extend(normalized)
        if self._store:
            self._store.append(normalized)

    @property
    def committed_updates(self) -> Iterable[KnowledgeUpdate]:
        return tuple(self._pending_updates)


class SimpleAgentGateway(AgentGatewayProtocol):
    """Maps agent names to Python callables for deterministic behavior."""

    def __init__(self, handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = handlers or {}

    def register(self, agent_name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._handlers[agent_name] = handler

    def invoke(self, agent_name: str, payload: Dict[str, Any]) -> Any:
        if agent_name not in self._handlers:
            raise KeyError(f"No handler registered for {agent_name!r}")
        return self._handlers[agent_name](payload)


class SimpleFeedbackRouter(FeedbackRouterProtocol):
    """Updates task state according to Agent3's decision payload."""

    def __init__(self, *, max_revisions: int = 2) -> None:
        self._max_revisions = max(0, max_revisions)

    def route(self, review_payload: Any, context: TaskContext) -> None:
        decision = None
        if isinstance(review_payload, dict):
            decision = review_payload.get("decision")

        context.set_artifact("agent3_feedback", review_payload)

        if decision == "approve":
            context.mark_state(TaskState.CODING)
            return

        if decision == "revise":
            count = int(context.get_artifact("revision_count", 0) or 0) + 1
            context.set_artifact("revision_count", count)
            if count > self._max_revisions:
                context.mark_state(TaskState.FAILED)
            else:
                context.mark_state(TaskState.BUILDING)
            return

        if decision == "reject":
            context.mark_state(TaskState.FAILED)
            return

        context.mark_state(TaskState.FAILED)


# ---------------------------------------------------------------------------
# Teaching helpers: default agent handlers
# ---------------------------------------------------------------------------


def default_agent1_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a simple task brief based on the user request and knowledge."""

    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    function_names = [item.name for item in snapshot.function_index]
    lesson_titles = [card.title for card in snapshot.lessons]

    return {
        "objective": payload.get("user_request", ""),
        "requirements": [
            "确认术语表或领域背景信息",
            "标注期望输出格式",
        ],
        "constraints": [
            "输出保持中文说明",
            "必要时引用函数索引",
        ],
        "tooling": {
            "available_functions": function_names,
        },
        "lessons": lesson_titles,
    }


def default_agent2_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a mock function specification to keep the loop running."""

    task_brief = payload.get("task_brief", {})
    objective = task_brief.get("objective", "")
    return {
        "name": "mock_function",
        "description": f"Helper function derived from objective: {objective}",
        "args": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
        "returns": "str",
        "requirements": ["使用伪实现"],
        "validation": ["待补充单元测试"],
        "ownership": "agent2-teaching-version",
    }


def default_agent3_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Approve by default; can be extended to simulate revisions."""

    return {
        "decision": "approve",
        "notes": "教学版自动通过。",
    }


def build_default_gateway() -> SimpleAgentGateway:
    """Convenience helper to construct a gateway with default handlers."""

    gateway = SimpleAgentGateway()
    gateway.register("agent1", default_agent1_handler)
    gateway.register("agent2", default_agent2_handler)
    gateway.register("agent3", default_agent3_handler)
    return gateway



def build_gemini_gateway(**kwargs) -> GeminiAgentGateway:
    """Construct a Gemini-backed gateway with optional overrides."""

    return GeminiAgentGateway(**kwargs)
