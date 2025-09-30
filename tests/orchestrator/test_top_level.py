"""Unit tests for the top-level data classes and protocols."""

from __future__ import annotations

import sys
import pathlib

# Add project root to path to allow absolute imports.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.top_level import TaskContext, KnowledgeUpdate, ConversationTurn, TaskState


def test_task_context_add_history():
    """Verify that a history turn is correctly added."""
    context = TaskContext(task_id="t1", user_request="ur1")
    context.add_history("user", "Hello")
    
    assert len(context.history) == 1
    assert isinstance(context.history[0], ConversationTurn)
    assert context.history[0].role == "user"
    assert context.history[0].content == "Hello"

def test_task_context_add_history_trims_to_limit():
    """Verify that history is trimmed when it exceeds the limit."""
    context = TaskContext(task_id="t1", user_request="ur1", history_limit=2)
    context.add_history("user", "First")
    context.add_history("model", "Second")
    context.add_history("user", "Third")
    
    assert len(context.history) == 2
    assert context.history[0].content == "Second"
    assert context.history[1].content == "Third"

def test_task_context_set_and_get_artifact():
    """Verify that artifacts can be set and retrieved."""
    context = TaskContext(task_id="t1", user_request="ur1")
    artifact_data = {"key": "value"}
    
    context.set_artifact("my_artifact", artifact_data)
    
    retrieved = context.get_artifact("my_artifact")
    assert retrieved == artifact_data
    assert context.get_artifact("non_existent", "default_val") == "default_val"

def test_task_context_append_knowledge_updates():
    """Verify that KnowledgeUpdate objects and dicts can be appended."""
    context = TaskContext(task_id="t1", user_request="ur1")
    
    # Append a KnowledgeUpdate object
    update_obj = KnowledgeUpdate(source="s1", category="c1", payload={})
    context.append_knowledge_updates(update_obj)
    
    # Append a dictionary
    update_dict = {"source": "s2", "category": "c2", "payload": {}}
    context.append_knowledge_updates(update_dict)
    
    # Append a list of both
    updates_list = [ 
        KnowledgeUpdate(source="s3", category="c3", payload={}),
        {"source": "s4", "category": "c4", "payload": {}},
    ]
    context.append_knowledge_updates(updates_list)
    
    final_updates = context.get_artifact("knowledge_updates")
    assert len(final_updates) == 4
    assert isinstance(final_updates[0], KnowledgeUpdate)
    assert isinstance(final_updates[1], KnowledgeUpdate)
    assert final_updates[0].source == "s1"
    assert final_updates[1].source == "s2"
    assert final_updates[2].source == "s3"
    assert final_updates[3].source == "s4"

# ---- Tests for TopLevelOrchestrator ----

from src.orchestrator.top_level import TopLevelOrchestrator
from src.orchestrator.support import (
    InMemoryTaskRegistry,
    InMemoryKnowledgeService,
    SimpleAgentGateway,
    SimpleFeedbackRouter,
    default_agent1_handler,
    default_agent2_handler,
)

def test_orchestrator_happy_path_run():
    """Verify a successful run where the review is approved on the first try."""
    # 1. Setup
    registry = InMemoryTaskRegistry()
    knowledge = InMemoryKnowledgeService()
    feedback_router = SimpleFeedbackRouter()
    
    # Setup a gateway with a simple, approving agent3
    gateway = SimpleAgentGateway()
    gateway.register("agent1", default_agent1_handler)
    gateway.register("agent2", default_agent2_handler)
    gateway.register("agent3", lambda _: {"decision": "approve"})
    
    orchestrator = TopLevelOrchestrator(registry, knowledge, gateway, feedback_router)
    
    # 2. Execute
    context = orchestrator.handle_new_task("test request")
    
    # 3. Assert
    assert context.task_state == TaskState.DONE
    assert context.get_artifact("task_brief") is not None
    assert context.get_artifact("function_spec") is not None
    assert context.get_artifact("agent3_review")["decision"] == "approve"

def test_orchestrator_handles_revision_loop():
    """Verify the orchestrator can handle a feedback loop (revise -> approve)."""
    # 1. Setup
    registry = InMemoryTaskRegistry()
    knowledge = InMemoryKnowledgeService()
    feedback_router = SimpleFeedbackRouter()
    
    # Setup a stateful agent3 that revises once, then approves
    agent3_call_count = 0
    def stateful_agent3_handler(payload):
        nonlocal agent3_call_count
        agent3_call_count += 1
        if agent3_call_count == 1:
            return {"decision": "revise"}
        return {"decision": "approve"}

    gateway = SimpleAgentGateway()
    gateway.register("agent1", default_agent1_handler)
    gateway.register("agent2", default_agent2_handler)
    gateway.register("agent3", stateful_agent3_handler)
    
    orchestrator = TopLevelOrchestrator(registry, knowledge, gateway, feedback_router)

    # 2. Execute
    context = orchestrator.handle_new_task("test request with revision")

    # 3. Assert
    assert context.task_state == TaskState.DONE
    assert agent3_call_count == 2
    assert context.get_artifact("revision_count") == 1

def test_orchestrator_fails_on_cycle_limit():
    """Verify the orchestrator fails if the revision loop exceeds max_cycles."""
    # 1. Setup
    registry = InMemoryTaskRegistry()
    knowledge = InMemoryKnowledgeService()
    feedback_router = SimpleFeedbackRouter()
    
    # agent3 that always asks for revisions
    gateway = SimpleAgentGateway()
    gateway.register("agent1", default_agent1_handler)
    gateway.register("agent2", default_agent2_handler)
    gateway.register("agent3", lambda _: {"decision": "revise"})
    
    # Set a low cycle limit
    orchestrator = TopLevelOrchestrator(registry, knowledge, gateway, feedback_router, max_cycles=2)

    # 2. Execute
    context = orchestrator.handle_new_task("test request for failure")

    # 3. Assert
    assert context.task_state == TaskState.FAILED
    last_error = context.get_artifact("last_error")
    assert last_error is not None
    assert last_error["error"] == "cycle_limit_reached"
