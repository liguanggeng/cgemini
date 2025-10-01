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
        self._chat: Optional[types.ChatSession] = None

    def invoke(self, agent_name: str, payload: Dict[str, Any]) -> Any:
        if agent_name == "agent1":
            # This method handles the first turn of a conversation with Agent1.
            # It creates and stores a chat session that can be used for subsequent turns.
            system_instruction = self._system_instruction or _build_agent1_prompt(payload)
            self._chat = self._client.chats.create(
                model=self._model,
                config=types.GenerateContentConfig(
                    temperature=self._temperature,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    system_instruction=system_instruction,
                ),
                history=payload.get("history", []),
            )

            prompt = payload.get("message_to_send", "")
            if not prompt:
                raise ValueError("Agent1 was invoked with no message to send.")

            response = self._chat.send_message(prompt)

            # The response is now processed by the orchestrator, which will decide
            # whether to continue the chat, call a function, or move to other agents.
            # We just return the raw response object here.
            return response

        # Existing logic for agent2 and agent3
        tools = []
        response_mime_type = "application/json"  # Default to JSON

        if agent_name == "agent2":
            if payload.get("mode") == "implement":
                prompt = _build_agent2_impl_prompt(payload)
                response_mime_type = "text/plain"  # Expecting raw code string
            else:
                prompt = _build_agent2_prompt(payload)

        elif agent_name == "agent3":
            prompt = _build_agent3_prompt(payload)

        else:
            raise ValueError(f"Unsupported agent '{agent_name}' for Gemini gateway")

        config = types.GenerateContentConfig(
            temperature=self._temperature,
            tools=tools,
        )
        if response_mime_type:
            config.response_mime_type = response_mime_type
        if self._system_instruction:
            config.system_instruction = self._system_instruction

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config,
        )

        if response_mime_type == "application/json":
            return _parse_json_response(response)
        return response.text


def _build_default_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    # Falls back to default environment configuration (may rely on Vertex env vars)
    return genai.Client()


def _build_agent1_prompt(payload: Dict[str, Any]) -> str:
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    
    with open("src/prompts/agent1_system.prompt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return prompt_template.format(
        function_index=_format_functions(snapshot.function_index),
        lessons=_format_lessons(snapshot.lessons),
        checklists=_format_checklists(snapshot.audit_checklists),
    )


def _build_agent2_prompt(payload: Dict[str, Any]) -> str:
    brief = payload.get("task_brief", {})
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    prior_artifacts = payload.get("prior_artifacts", {})
    sanitized_artifacts = _stringify_for_prompt(prior_artifacts)

    with open("src/prompts/agent2_design.prompt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Populate the template with actual data.
    return prompt_template.format(
        task_brief_json=json.dumps(brief, ensure_ascii=False, indent=2),
        knowledge_snapshot_json=json.dumps(
            {
                "function_index": _format_functions(snapshot.function_index),
                "lessons": _format_lessons(snapshot.lessons),
            },
            ensure_ascii=False,
            indent=2,
        ),
        prior_artifacts_json=json.dumps(sanitized_artifacts, ensure_ascii=False, indent=2),
    )

def _build_agent2_impl_prompt(payload: Dict[str, Any]) -> str:
    """Builds the prompt for Agent2's implementation phase."""
    spec = payload.get("function_spec", {})
    
    with open("src/prompts/agent2_implement.prompt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return prompt_template.format(
        function_spec_json=json.dumps(spec, ensure_ascii=False, indent=2)
    )



def _build_agent3_prompt(payload: Dict[str, Any]) -> str:
    spec = payload.get("function_spec", {})
    snapshot: KnowledgeSnapshot = payload.get("knowledge", KnowledgeSnapshot())
    
    with open("src/prompts/agent3_review.prompt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return prompt_template.format(
        spec_json=json.dumps(spec, ensure_ascii=False, indent=2),
        checklists_json=_format_checklists(snapshot.audit_checklists),
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


    def continue_chat_with_function_result(
        self, function_name: str, function_response: Dict[str, Any]
    ) -> types.GenerateContentResponse:
        """
        Continues the existing chat by sending the result of a function call.

        Args:
            function_name: The name of the function that was called.
            function_response: The dictionary returned by the worker (containing either 'result' or 'error').

        Returns:
            The final GenerateContentResponse from the model.
        """
        if not self._chat:
            raise ValueError("Cannot continue chat without an active chat session.")

        # Construct the function response part for the API
        response_part = types.Part.from_dict({
            "function_response": {
                "name": function_name,
                "response": function_response,
            }
        })

        # Send the function response back to the model
        response = self._chat.send_message(response_part)

        # The turn is complete, reset the chat session
        self._chat = None

        return response


__all__ = ["GeminiAgentGateway"]
