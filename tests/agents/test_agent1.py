"""Unit tests for Agent1's teaching handler."""

from __future__ import annotations

import sys
import pathlib

# Add project root to path to allow absolute imports.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.agent1 import teaching_handler
from src.orchestrator.top_level import KnowledgeSnapshot, FunctionSummary, LessonCard

def test_teaching_handler_produces_correct_structure():
    """Verify the handler returns a dict with all the expected top-level keys."""
    payload = {"user_request": "test"}
    result = teaching_handler(payload)
    
    expected_keys = [
        "objective",
        "requirements",
        "constraints",
        "tooling",
        "open_questions",
        "lessons_applied",
        "lessons_to_add",
    ]
    
    assert all(key in result for key in expected_keys)
    assert isinstance(result["tooling"], dict)

def test_teaching_handler_with_empty_knowledge():
    """Verify the handler's output when no prior knowledge is provided."""
    payload = {"user_request": "A task with no prior knowledge"}
    result = teaching_handler(payload)
    
    assert result["objective"] == "A task with no prior knowledge"
    assert result["tooling"]["reuse"] == []
    assert result["tooling"]["gaps"] == ["需要新增函数来满足需求"]
    assert result["lessons_applied"] == []

def test_teaching_handler_with_knowledge():
    """Verify the handler correctly uses the provided knowledge snapshot."""
    snapshot = KnowledgeSnapshot(
        function_index=[
            FunctionSummary(name="func1", description="d1"),
            FunctionSummary(name="func2", description="d2"),
        ],
        lessons=[
            LessonCard(lesson_id="l1", title="title1", content="c1"),
        ]
    )
    payload = {"user_request": "A task with knowledge", "knowledge": snapshot}
    
    result = teaching_handler(payload)
    
    assert result["tooling"]["reuse"] == ["func1", "func2"]
    assert result["tooling"]["gaps"] == []
    assert result["lessons_applied"] == ["title1"]
