"""Unit tests for orchestrator support components."""

from __future__ import annotations

import sys
import pathlib
import json

# Add project root to path to allow absolute imports.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.support import InMemoryTaskRegistry
from src.orchestrator.top_level import TaskState


def test_task_registry_can_register_new_task():
    """Verify that a new task can be registered and receives a unique ID."""
    registry = InMemoryTaskRegistry()
    
    user_request_1 = "First task"
    task_id_1 = registry.register(user_request_1)
    
    user_request_2 = "Second task"
    task_id_2 = registry.register(user_request_2)

    assert task_id_1 is not None
    assert task_id_2 is not None
    assert task_id_1 != task_id_2
    assert task_id_1.startswith("task-")

def test_task_registry_initial_state_is_pending():
    """Verify that a newly registered task has a PENDING state."""
    registry = InMemoryTaskRegistry()
    task_id = registry.register("A new task")
    
    task = registry.get(task_id)
    
    assert task is not None
    assert task["state"] == TaskState.PENDING
    assert task["request"] == "A new task"

def test_task_registry_can_update_state():
    """Verify that the state of a task can be updated."""
    registry = InMemoryTaskRegistry()
    task_id = registry.register("Task to be updated")
    
    registry.update_state(task_id, TaskState.BUILDING)
    task = registry.get(task_id)
    
    assert task is not None
    assert task["state"] == TaskState.BUILDING

def test_task_registry_get_returns_none_for_unknown_id():
    """Verify that getting a non-existent task returns None."""
    registry = InMemoryTaskRegistry()
    task = registry.get("unknown-task-id")
    
    assert task is None

# ---- Tests for InMemoryKnowledgeService ----

from src.orchestrator.support import InMemoryKnowledgeService
from src.orchestrator.top_level import FunctionSummary, LessonCard, KnowledgeUpdate, TaskContext

def test_knowledge_service_loads_initial_snapshot():
    """Verify that the service returns the snapshot it was initialized with."""
    functions = [FunctionSummary(name="f1", description="d1")]
    lessons = [LessonCard(lesson_id="l1", title="t1", content="c1")]
    service = InMemoryKnowledgeService(function_index=functions, lessons=lessons)
    
    snapshot = service.load_snapshot()
    
    assert snapshot.function_index == functions
    assert snapshot.lessons == lessons
    assert snapshot.audit_checklists == []

def test_knowledge_service_commits_updates_to_internal_list(tmp_path: pathlib.Path):
    """Verify that committed updates are stored in the service."""
    service = InMemoryKnowledgeService(store_path=tmp_path / "test.jsonl")
    update = KnowledgeUpdate(source="test", category="test", payload={})
    
    service.commit_updates([update])
    
    committed = list(service.committed_updates)
    assert len(committed) == 1
    assert committed[0] == update

def test_knowledge_service_commits_updates_to_store(tmp_path: pathlib.Path):
    """Verify that committing updates also writes them to the KnowledgeStore."""
    store_path = tmp_path / "knowledge.jsonl"
    service = InMemoryKnowledgeService(store_path=store_path)
    update = KnowledgeUpdate(source="agent2", category="function", payload={"name": "new_func"})

    service.commit_updates([update])

    # Verify by reading the file content directly
    assert store_path.exists()
    content = store_path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["source"] == "agent2"
    assert data["payload"] == {"name": "new_func"}

# ---- Tests for SimpleFeedbackRouter ----

from src.orchestrator.support import SimpleFeedbackRouter

class MockTaskContext:
    """A mock TaskContext to intercept state changes for testing."""
    def __init__(self):
        self.state = TaskState.REVIEWING
        self.artifacts = {}

    def mark_state(self, state: TaskState):
        self.state = state

    def set_artifact(self, key: str, value: any):
        self.artifacts[key] = value

    def get_artifact(self, key: str, default: any = None) -> any:
        return self.artifacts.get(key, default)

def test_feedback_router_approves_task():
    """Verify 'approve' decision moves task state to DONE."""
    router = SimpleFeedbackRouter()
    context = MockTaskContext()
    review = {"decision": "approve"}
    
    router.route(review, context)
    
    assert context.state == TaskState.DONE
    assert context.artifacts["agent3_feedback"] == review

def test_feedback_router_revises_task():
    """Verify 'revise' decision moves task state to BUILDING."""
    router = SimpleFeedbackRouter()
    context = MockTaskContext()
    review = {"decision": "revise"}
    
    router.route(review, context)
    
    assert context.state == TaskState.BUILDING
    assert context.artifacts["revision_count"] == 1

def test_feedback_router_rejects_task():
    """Verify 'reject' decision moves task state to FAILED."""
    router = SimpleFeedbackRouter()
    context = MockTaskContext()
    review = {"decision": "reject"}
    
    router.route(review, context)
    
    assert context.state == TaskState.FAILED

def test_feedback_router_fails_on_unknown_decision():
    """Verify that any decision other than 'approve' or 'revise' leads to FAILED."""
    router = SimpleFeedbackRouter()
    context = MockTaskContext()
    review = {"decision": "unknown_decision"}
    
    router.route(review, context)
    
    assert context.state == TaskState.FAILED

def test_feedback_router_exceeds_revision_limit():
    """Verify that 'revise' leads to FAILED if max_revisions is exceeded."""
    router = SimpleFeedbackRouter(max_revisions=1)
    context = MockTaskContext()
    context.set_artifact("revision_count", 1)
    review = {"decision": "revise"}
    
    router.route(review, context)
    
    assert context.state == TaskState.FAILED
    assert context.artifacts["revision_count"] == 2
