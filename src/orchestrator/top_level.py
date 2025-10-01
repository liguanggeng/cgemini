"""Top-level orchestrator scaffolding.

This module contains the skeleton code for coordinating Agent1, Agent2, and Agent3.
The concrete implementations of registries, knowledge services, and agent gateways
will be introduced in later iterations.
"""

from __future__ import annotations

import logging
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
from google.genai import types
from src.worker import worker

_DEFAULT_MAX_CYCLES = 5
_DEFAULT_HISTORY_LIMIT = 50


class TaskState(str, Enum):
    """Lifecycle states for a task handled by the orchestrator."""

    PENDING = "pending"
    CLARIFYING = "clarifying"
    BUILDING = "building"
    REVIEWING = "reviewing"
    CODING = "coding"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ConversationTurn:
    """Stores one exchange within the task history."""

    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class FunctionSummary:
    """Lightweight view of a function that may be reused by Agent1 and Agent2."""

    name: str
    description: str
    tags: List[str] = field(default_factory=list)


@dataclass
class LessonCard:
    """Captures a reusable lesson or reminder for future tasks."""

    lesson_id: str
    title: str
    content: str


@dataclass
class Checklist:
    """Represents a review checklist used by Agent3."""

    name: str
    items: List[str]


@dataclass
class KnowledgeUpdate:
    """Structured record describing knowledge changes produced during a task."""

    source: str
    category: str
    payload: Dict[str, Any]
    notes: Optional[Any] = None

    def as_dict(self) -> Dict[str, Any]:
        """Return a serializable representation suitable for persistence."""

        record = {
            "source": self.source,
            "category": self.category,
            "payload": self.payload,
        }
        if self.notes is not None:
            record["notes"] = self.notes
        return record


@dataclass
class KnowledgeSnapshot:
    """Aggregates references that the orchestrator shares with agents."""

    function_index: List[FunctionSummary] = field(default_factory=list)
    lessons: List[LessonCard] = field(default_factory=list)
    audit_checklists: List[Checklist] = field(default_factory=list)


@dataclass
class TaskContext:
    """Holds the mutable state associated with a single task."""

    task_id: str
    user_request: str
    task_state: TaskState = TaskState.PENDING
    history: List[ConversationTurn] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    knowledge_refs: KnowledgeSnapshot = field(default_factory=KnowledgeSnapshot)
    history_limit: int = _DEFAULT_HISTORY_LIMIT

    def add_history(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a new turn and keep the history within the configured limit."""

        self.history.append(ConversationTurn(role=role, content=content, metadata=metadata))
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit :]

    def set_artifact(self, key: str, value: Any) -> None:
        """Store or override an artifact produced during orchestration."""

        self.artifacts[key] = value

    def get_artifact(self, key: str, default: Any = None) -> Any:
        """Return an artifact while providing a default when missing."""

        return self.artifacts.get(key, default)

    def append_knowledge_updates(
        self,
        updates: Union[
            KnowledgeUpdate,
            Iterable[KnowledgeUpdate],
            Dict[str, Any],
            Iterable[Dict[str, Any]],
        ],
    ) -> None:
        """Record knowledge updates using a normalized dataclass container."""

        if not updates:
            return

        existing = self.artifacts.get("knowledge_updates")
        store: List[KnowledgeUpdate] = []
        if existing:
            if isinstance(existing, list):
                store.extend(self._coerce_knowledge_update(item) for item in existing if item)
            else:
                store.append(self._coerce_knowledge_update(existing))

        if isinstance(updates, KnowledgeUpdate):
            normalized = [updates]
        elif isinstance(updates, dict):
            normalized = [self._coerce_knowledge_update(updates)]
        elif isinstance(updates, Iterable):
            normalized = [self._coerce_knowledge_update(item) for item in updates if item]
        else:
            normalized = [self._coerce_knowledge_update(updates)]

        store.extend(normalized)
        self.artifacts["knowledge_updates"] = store

    @staticmethod
    def _coerce_knowledge_update(item: Any) -> KnowledgeUpdate:
        """Normalize arbitrary inputs into a KnowledgeUpdate instance."""

        if isinstance(item, KnowledgeUpdate):
            return item
        if isinstance(item, dict):
            source = str(item.get("source", "unknown"))
            category = str(item.get("category", "misc"))
            notes = item.get("notes")
            payload = item.get("payload")
            if payload is None:
                payload = {k: v for k, v in item.items() if k not in {"source", "category", "notes"}}
            elif not isinstance(payload, dict):
                payload = {"value": payload}
            return KnowledgeUpdate(source=source, category=category, payload=payload, notes=notes)
        return KnowledgeUpdate(source="unknown", category="raw", payload={"value": item})

    def mark_state(self, state: TaskState) -> None:
        """Update the task state stored on the context."""

        self.task_state = state


class TopLevelOrchestrator:
    """Coordinates the work of Agent1, Agent2, and Agent3."""

    def __init__(
        self,
        task_registry,
        knowledge_service,
        agent_gateway,
        feedback_router,
        worker,  # New dependency
        *,
        max_cycles: int = _DEFAULT_MAX_CYCLES,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._task_registry = task_registry
        self._knowledge_service = knowledge_service
        self._agent_gateway = agent_gateway
        self._feedback_router = feedback_router
        self._worker = worker  # New attribute
        self._max_cycles = max(1, max_cycles)
        self._logger = logger or logging.getLogger(__name__)

    def handle_new_task(self, user_request: str) -> TaskContext:
        """Bootstrap context and process the first turn of the conversation."""
        context = self._bootstrap_context(user_request)
        return self._process_agent1_turn(context)

    def handle_user_reply(self, context: TaskContext, user_reply: str) -> TaskContext:
        """Handles a user's reply to a clarifying question from Agent1."""
        context.add_history("user", user_reply)
        return self._process_agent1_turn(context)

    def _process_agent1_turn(self, context: TaskContext) -> TaskContext:
        """Drives a single turn of interaction with Agent1 and routes the result."""
        # The first drive gets the initial response (could be text, function call, or task brief)
        ok, agent1_response = self._safe_drive(self._drive_agent1, context, "agent1")
        if not ok:
            self._finalize(context)
            return context

        # The response object itself contains the different possibilities.
        part = agent1_response.candidates[0].content.parts[0]

        # Case 1: Agent1 returned a FunctionCall request
        if part.function_call:
            function_call = part.function_call
            # Log the model's decision to call a function
            context.add_history(
                role="model",
                content="",  # No text content when a function is called
                metadata={"function_call": function_call._pb.to_dict() if hasattr(function_call, '_pb') else str(function_call)}
            )

            # Execute the function using the worker
            execution_result = self._worker.execute_function(function_call.name, function_call.args)

            # Log the result of the execution
            context.add_history(
                role="tool",  # Special role for function responses
                content="",
                metadata={"function_response": execution_result}
            )

            # Second drive: Send the result back to the model to get a final summary
            final_response = self._agent_gateway.continue_chat_with_function_result(
                function_name=function_call.name,
                function_response=execution_result,
            )

            # Log the final text response from the model
            context.add_history("model", final_response.text)
            context.mark_state(TaskState.DONE) # Mark as DONE for this flow

        # Case 2: Agent1 returned a structured task brief for Agent2
        elif "objective" in agent1_response.text: # Heuristic to check for JSON
            try:
                task_brief = json.loads(agent1_response.text)
                context.set_artifact("task_brief", task_brief)
                context.add_history("agent1", self._summarize_for_history(task_brief), {"artifact": "task_brief"})
                context.mark_state(TaskState.BUILDING)
                # The conversation with Agent1 is over; proceed with the downstream agents.
                return self._continue_with_downstream_agents(context)
            except json.JSONDecodeError:
                # It looked like a task brief, but wasn't valid JSON. Treat as text.
                context.add_history("model", agent1_response.text)
                context.mark_state(TaskState.CLARIFYING)

        # Case 3: Agent1 returned a simple text response (chat)
        else:
            context.add_history("model", agent1_response.text)
            context.mark_state(TaskState.CLARIFYING)

        self._finalize(context)
        return context

    def _continue_with_downstream_agents(self, context: TaskContext) -> TaskContext:
        """Runs the Agent2 -> Agent3 loop until the task is done or fails."""
        cycle = 0
        while context.task_state not in (TaskState.DONE, TaskState.FAILED):
            if cycle >= self._max_cycles:
                self._logger.error("Agent loop exceeded max cycles for task %s", context.task_id)
                context.set_artifact("last_error", {"error": "cycle_limit_reached"})
                context.mark_state(TaskState.FAILED)
                break

            cycle += 1

            if context.task_state == TaskState.CODING:
                ok, _ = self._safe_drive(self._drive_agent2_for_impl, context, "agent2_implement")
                if ok:
                    context.mark_state(TaskState.DONE)
                continue

            ok, _ = self._safe_drive(self._drive_agent2, context, "agent2")
            if not ok:
                break

            ok, review_payload = self._safe_drive(self._drive_agent3, context, "agent3")
            if not ok:
                break

            context.set_artifact("agent3_review", review_payload)

            def feedback_step(ctx: TaskContext):
                self._apply_feedback(ctx, review_payload)

            ok, _ = self._safe_drive(feedback_step, context, "feedback_router")
            if not ok:
                break

            time.sleep(1) # Avoid rapid-fire API calls in case of loops

        self._finalize(context)
        return context

    def _bootstrap_context(self, user_request: str) -> TaskContext:
        """Create a context object and pull a knowledge snapshot."""
        task_id = self._task_registry.register(user_request)
        snapshot = self._knowledge_service.load_snapshot()
        context = TaskContext(task_id=task_id, user_request=user_request, knowledge_refs=snapshot)
        context.mark_state(TaskState.CLARIFYING)
        self._task_registry.update_state(task_id, context.task_state)
        context.add_history(
            role="system",
            content=f"task_registered:{task_id}",
            metadata={"user_request": user_request},
        )
        # Add the first user message to history
        context.add_history("user", user_request)
        return context

    def _drive_agent1(self, context: TaskContext) -> Any:
        """Trigger Agent1 and return the raw result."""

        # The full conversational history for the API
        api_history = [turn for turn in context.history if turn.role in ["user", "model"]]

        if not api_history or api_history[-1].role != "user":
            # This can happen if the first turn is not from the user, which shouldn't occur in our flow.
            raise ValueError("Trying to drive Agent1 without a recent user message.")

        message_to_send = api_history[-1].content
        history_for_api = api_history[:-1]

        payload = {
            "message_to_send": message_to_send,
            "history": history_for_api,
            "knowledge": context.knowledge_refs,
            "user_request": context.user_request,  # Pass original request for context in system prompt
        }
        return self._agent_gateway.invoke("agent1", payload)

    def _drive_agent2(self, context: TaskContext) -> None:
        """Trigger Agent2 with the latest brief and knowledge."""
        payload = {
            "task_brief": context.get_artifact("task_brief"),
            "knowledge": context.knowledge_refs,
            "prior_artifacts": context.artifacts,
        }
        result = self._agent_gateway.invoke("agent2", payload)
        context.set_artifact("function_spec", result)
        context.add_history("agent2", self._summarize_for_history(result), {"artifact": "function_spec"})
        context.mark_state(TaskState.REVIEWING)
        self._task_registry.update_state(context.task_id, context.task_state)
        if isinstance(result, dict):
            updates_payload = result.get("knowledge_updates")
            if updates_payload:
                context.append_knowledge_updates(
                    self._wrap_knowledge_payload("agent2", "function_update", updates_payload)
                )

    def _drive_agent3(self, context: TaskContext) -> Any:
        """Trigger Agent3 to review the proposed function specification."""
        payload = {
            "function_spec": context.get_artifact("function_spec"),
            "knowledge": context.knowledge_refs,
        }
        result = self._agent_gateway.invoke("agent3", payload)
        context.add_history("agent3", self._summarize_for_history(result))
        if isinstance(result, dict):
            updates_payload = result.get("knowledge_updates")
            if updates_payload:
                context.append_knowledge_updates(
                    self._wrap_knowledge_payload("agent3", "review", updates_payload)
                )
        return result

    def _drive_agent2_for_impl(self, context: TaskContext) -> None:
        """Trigger Agent2 in 'implement' mode to generate Python code."""
        payload = {
            "mode": "implement",
            "function_spec": context.get_artifact("function_spec"),
            "knowledge": context.knowledge_refs,
        }
        result_code = self._agent_gateway.invoke("agent2", payload)
        context.set_artifact("function_impl", result_code)
        context.add_history("agent2", self._summarize_for_history(result_code), {"artifact": "function_impl"})

    def _apply_feedback(self, context: TaskContext, review_payload: Any) -> None:
        """Route Agent3 feedback and persist task state transitions."""
        self._feedback_router.route(review_payload, context)
        self._task_registry.update_state(context.task_id, context.task_state)

    def _finalize(self, context: TaskContext) -> None:
        """Persist closing state and commit knowledge updates if needed."""
        self._task_registry.update_state(context.task_id, context.task_state)
        if context.task_state == TaskState.DONE:
            self._persist_function_artifacts(context)
        updates = self._collect_knowledge_updates(context)
        if updates:
            self._knowledge_service.commit_updates(updates)

    def _persist_function_artifacts(self, context: TaskContext) -> None:
        """Save the function spec and implementation and update the tool registry."""
        function_spec = context.get_artifact("function_spec")
        function_impl = context.get_artifact("function_impl")
        if not (isinstance(function_spec, dict) and isinstance(function_impl, str)):
            self._logger.warning("Skipping function persistence for task %s due to missing artifacts.", context.task_id)
            return
        func_name = function_spec.get("name")
        if not func_name:
            self._logger.warning("Skipping function persistence for task %s because function name is missing.", context.task_id)
            return
        tools_dir = Path("tools")
        tools_dir.mkdir(exist_ok=True)
        spec_path = tools_dir / f"{func_name}.json"
        impl_path = tools_dir / f"{func_name}.py"
        registry_path = tools_dir / "registry.json"
        spec_json = json.dumps(function_spec, indent=2, ensure_ascii=False)
        spec_path.write_text(spec_json, encoding="utf-8")
        impl_path.write_text(function_impl, encoding="utf-8")
        registry = {}
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._logger.warning("Could not parse tool registry, creating a new one.")
        registry[func_name] = {
            "description": function_spec.get("description", ""),
            "version": "1.0",
            "status": "active",
            "declaration_path": str(spec_path),
            "implementation_path": str(impl_path),
        }
        registry_json = json.dumps(registry, indent=2, ensure_ascii=False)
        registry_path.write_text(registry_json, encoding="utf-8")
        context.add_history("system", f"Function {func_name} persisted and registered in {registry_path}")

    def _safe_drive(
        self,
        step: Callable[[TaskContext], Any],
        context: TaskContext,
        stage_name: str,
    ) -> Tuple[bool, Any]:
        """Execute a pipeline step and capture unexpected failures."""
        try:
            return True, step(context)
        except Exception as exc:
            self._logger.exception("Stage '%s' failed for task %s", stage_name, context.task_id)
            context.add_history(
                role=stage_name,
                content="error",
                metadata={
                    "error": str(exc),
                    "exception_type": exc.__class__.__name__,
                },
            )
            context.set_artifact("last_error", {"stage": stage_name, "error": str(exc)})
            context.mark_state(TaskState.FAILED)
            self._task_registry.update_state(context.task_id, context.task_state)
            return False, None

    @staticmethod
    def _summarize_for_history(payload: Any, *, limit: int = 800) -> str:
        """Return a compact string representation for history storage."""
        text = str(payload)
        return text if len(text) <= limit else f"{text[: limit - 3]}..."

    @staticmethod
    def _wrap_knowledge_payload(source: str, category: str, raw: Any) -> List[KnowledgeUpdate]:
        """Convert heterogeneous inputs into KnowledgeUpdate instances."""
        if isinstance(raw, list):
            updates: List[KnowledgeUpdate] = []
            for item in raw:
                updates.extend(TopLevelOrchestrator._wrap_knowledge_payload(source, category, item))
            return updates
        if isinstance(raw, KnowledgeUpdate):
            return [raw]
        if isinstance(raw, dict):
            payload = raw.get("payload")
            if payload is None:
                payload = {k: v for k, v in raw.items() if k not in {"source", "category", "notes"}}
            elif not isinstance(payload, dict):
                payload = {"value": payload}
            return [
                KnowledgeUpdate(
                    source=str(raw.get("source", source)),
                    category=str(raw.get("category", category)),
                    payload=payload,
                    notes=raw.get("notes"),
                )
            ]
        return [KnowledgeUpdate(source=source, category=category, payload={"value": raw})]

    @staticmethod
    def _collect_knowledge_updates(context: TaskContext) -> List[KnowledgeUpdate]:
        """Gather normalized knowledge updates from the context artifacts."""
        updates_field = context.get_artifact("knowledge_updates")
        if not updates_field:
            return []
        items = updates_field if isinstance(updates_field, list) else [updates_field]
        return [TaskContext._coerce_knowledge_update(item) for item in items if item]


class TaskRegistryProtocol:
    """Expected interface of the task registry used by the orchestrator."""

    def register(self, user_request: str) -> str:  # pragma: no cover - placeholder
        raise NotImplementedError

    def update_state(self, task_id: str, state: TaskState) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError


class KnowledgeServiceProtocol:
    """Expected interface of the knowledge service."""

    def load_snapshot(self) -> KnowledgeSnapshot:  # pragma: no cover - placeholder
        raise NotImplementedError

    def commit_updates(self, updates: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError


class AgentGatewayProtocol:
    """Expected interface of the agent invocation layer."""

    def invoke(self, agent_name: str, payload: Dict[str, Any]) -> Any:  # pragma: no cover - placeholder
        raise NotImplementedError


class FeedbackRouterProtocol:
    """Expected interface of the feedback router component."""

    def route(self, review_payload: Any, context: TaskContext) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError
