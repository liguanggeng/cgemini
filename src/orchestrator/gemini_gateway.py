"""Gemini-powered agent gateway for the orchestrator.

This module adapts the AgentGatewayProtocol to Google Gemini via the
``google-genai`` client. It provides agent-specific prompts so that the
orchestrator can drive the multi-agent workflow with real model calls.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

from google import genai
from google.genai import types

from .top_level import AgentGatewayProtocol, KnowledgeSnapshot, KnowledgeUpdate

_DEFAULT_MODEL = (
    os.getenv('GEMINI_MODEL')
    or os.getenv('GOOGLE_GENAI_MODEL')
    or os.getenv('DEFAULT_MODEL')
    or 'gemini-2.0-flash-001'
)
_DEFAULT_TEMPERATURE = 0.3


class GeminiAgentGateway(AgentGatewayProtocol):
    """Invoke Google Gemini models for each orchestrator agent."""

    def __init__(
        self,
        *,
        client: Optional[genai.Client] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        system_instruction: Optional[str] = None,
    ) -> None:
        self._client = client or _build_default_client()
        self._model = model or _DEFAULT_MODEL
        self._temperature = temperature if temperature is not None else _DEFAULT_TEMPERATURE
        self._system_instruction = system_instruction

    def invoke(self, agent_name: str, payload: Dict[str, Any]) -> Any:
        if agent_name == "agent1":
            prompt = _build_agent1_prompt(payload)
        elif agent_name == "agent2":
            prompt = _build_agent2_prompt(payload)
        elif agent_name == "agent3":
            prompt = _build_agent3_prompt(payload)
        else:
            raise ValueError(f"Unsupported agent '{agent_name}' for Gemini gateway")

        config = types.GenerateContentConfig(
            temperature=self._temperature,
            response_mime_type="application/json",
        )
        if self._system_instruction:
            config.system_instruction = self._system_instruction

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )
        return _parse_json_response(response)


def _build_default_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    # Falls back to default environment configuration (may rely on Vertex env vars)
    return genai.Client()


def _build_agent1_prompt(payload: Dict[str, Any]) -> str:
    request = payload.get("user_request", "")
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    return (
        "你是需求编排专家，只整理用户任务，不写代码。\n"
        "请阅读用户需求和知识快照，返回 JSON 对象，字段包括：\n"
        "objective, requirements (array), constraints (array), tooling(reuse/gaps/notes),\n"
        "open_questions, lessons_applied, lessons_to_add。\n"
        "JSON 必须有效且符合 UTF-8。\n"
        "\n"
        f"[用户需求]\n{request}\n\n"
        f"[可复用函数]\n{_format_functions(snapshot.function_index)}\n\n"
        f"[经验卡]\n{_format_lessons(snapshot.lessons)}\n\n"
        f"[审核检查单]\n{_format_checklists(snapshot.audit_checklists)}\n"
    )


def _build_agent2_prompt(payload: Dict[str, Any]) -> str:
    brief = payload.get("task_brief", {})
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    prior_artifacts = payload.get("prior_artifacts", {})
    sanitized_artifacts = _stringify_for_prompt(prior_artifacts)

    return (
        "?????????????? Gemini Function Call ????????\n"
        "??? JSON??????name, description, args(JSON Schema), returns, requirements,\n"
        "validation(??), ownership, knowledge_updates(??????????)?\n"
        "\n"
        f"[????]\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"[????]\n{json.dumps(sanitized_artifacts, ensure_ascii=False, indent=2)}\n\n"
        f"[????]\n????: {_format_functions(snapshot.function_index)}\n"
        f"???: {_format_lessons(snapshot.lessons)}\n"
        f"????: {_format_checklists(snapshot.audit_checklists)}\n"
    )

def _build_agent3_prompt(payload: Dict[str, Any]) -> str:
    spec = payload.get("function_spec", {})
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    return (
        "你是函数资产审核官。请审查候选函数，并返回 JSON：\n"
        "decision(approve/revise/reject), summary, issues(数组，可空),\n"
        "actions(建议), knowledge_updates(可选，用于沉淀)。\n"
        "\n"
        f"[候选函数]\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n\n"
        f"[审核检查单]\n{_format_checklists(snapshot.audit_checklists)}\n"
    )


def _parse_json_response(response: types.GenerateContentResponse) -> Any:
    text = response.text or ""
    if not text and response.candidates:
        text = "\n".join(candidate.content.parts[0].text for candidate in response.candidates if candidate.content.parts)
    text = text.strip()
    if not text:
        raise ValueError("Gemini response is empty")
    # Some models may wrap JSON in code fences.
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return json.loads(text)


def _stringify_for_prompt(value: Any) -> Any:
    """Recursively convert artifacts into JSON-serializable objects."""

    if isinstance(value, KnowledgeUpdate):
        return value.as_dict()
    if isinstance(value, dict):
        return {key: _stringify_for_prompt(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_stringify_for_prompt(item) for item in value]
    return value


def _format_functions(functions: Iterable[Any]) -> str:
    return "\n".join(f"- {item.name}: {item.description}" for item in functions) or "(无)"


def _format_lessons(lessons: Iterable[Any]) -> str:
    return "\n".join(f"- {card.title}" for card in lessons) or "(无)"


def _format_checklists(checklists: Iterable[Any]) -> str:
    lines = []
    for checklist in checklists:
        lines.append(f"- {checklist.name}: {'、'.join(checklist.items)}")
    return "\n".join(lines) or "(无)"


__all__ = ["GeminiAgentGateway"]
