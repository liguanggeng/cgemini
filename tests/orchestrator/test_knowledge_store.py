"""Unit tests for the KnowledgeStore component."""

from __future__ import annotations

import sys
import pathlib
import json

# Add project root to path to allow absolute imports.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator.knowledge_store import KnowledgeStore
from src.orchestrator.top_level import KnowledgeUpdate


def test_knowledge_store_read_all_on_non_existent_file(tmp_path: pathlib.Path):
    """Verify that reading from a non-existent store returns an empty list."""
    store_path = tmp_path / "test.jsonl"
    store = KnowledgeStore(store_path)
    
    assert store.read_all() == []

def test_knowledge_store_can_append_and_read_single_update(tmp_path: pathlib.Path):
    """Verify a single KnowledgeUpdate can be written and read back."""
    store_path = tmp_path / "test.jsonl"
    store = KnowledgeStore(store_path)
    
    update = KnowledgeUpdate(source="agent1", category="lesson", payload={"key": "value"})
    store.append([update])
    
    read_updates = store.read_all()
    
    assert len(read_updates) == 1
    assert read_updates[0].source == "agent1"
    assert read_updates[0].category == "lesson"
    assert read_updates[0].payload == {"key": "value"}

def test_knowledge_store_handles_multiple_appends(tmp_path: pathlib.Path):
    """Verify that the store correctly appends records across multiple calls."""
    store_path = tmp_path / "test.jsonl"
    store = KnowledgeStore(store_path)
    
    update1 = KnowledgeUpdate(source="agent1", category="cat1", payload={})
    update2 = KnowledgeUpdate(source="agent2", category="cat2", payload={})
    
    store.append([update1])
    store.append([update2])
    
    read_updates = store.read_all()
    
    assert len(read_updates) == 2
    assert read_updates[0].source == "agent1"
    assert read_updates[1].source == "agent2"

def test_knowledge_store_persists_data_to_file(tmp_path: pathlib.Path):
    """Verify that data is physically written to the JSONL file."""
    store_path = tmp_path / "test.jsonl"
    store = KnowledgeStore(store_path)
    
    updates = [
        KnowledgeUpdate(source="s1", category="c1", payload={"p": 1}),
        KnowledgeUpdate(source="s2", category="c2", payload={"p": 2}),
    ]
    store.append(updates)
    
    # Verify file content directly
    lines = store_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    
    data1 = json.loads(lines[0])
    data2 = json.loads(lines[1])
    
    assert data1["source"] == "s1"
    assert data1["payload"] == {"p": 1}
    assert data2["source"] == "s2"
    assert data2["payload"] == {"p": 2}
