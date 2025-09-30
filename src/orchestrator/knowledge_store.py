"""Local disk persistence helpers for knowledge updates."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterable, List

from .top_level import KnowledgeUpdate

_lock = threading.Lock()


class KnowledgeStore:  # pragma: no cover - lightweight helper
    """Append-only store that saves KnowledgeUpdate items to a JSONL file."""

    def __init__(self, path: os.PathLike[str] | str, *, ensure_dir: bool = True) -> None:
        self._path = Path(path)
        if ensure_dir:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, updates: Iterable[KnowledgeUpdate]) -> None:
        entries = [_coerce(update).as_dict() for update in updates]
        if not entries:
            return
        payload = "\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n"
        with _lock:
            existing = self._path.read_text(encoding="utf-8") if self._path.exists() else ""
            self._path.write_text(existing + payload, encoding="utf-8")

    def read_all(self) -> List[KnowledgeUpdate]:
        if not self._path.exists():
            return []
        result: List[KnowledgeUpdate] = []
        with _lock:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                result.append(
                    KnowledgeUpdate(
                        source=data.get("source", "unknown"),
                        category=data.get("category", "misc"),
                        payload=data.get("payload", {}),
                        notes=data.get("notes"),
                    )
                )
        return result


def _coerce(value: KnowledgeUpdate | dict) -> KnowledgeUpdate:
    if isinstance(value, KnowledgeUpdate):
        return value
    if isinstance(value, dict):
        return KnowledgeUpdate(
            source=str(value.get("source", "unknown")),
            category=str(value.get("category", "misc")),
            payload=value.get("payload", {}),
            notes=value.get("notes"),
        )
    raise TypeError(f"Unsupported knowledge update type: {type(value)!r}")
