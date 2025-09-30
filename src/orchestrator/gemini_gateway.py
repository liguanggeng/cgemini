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
        # Determine prompt and response MIME type based on agent and mode.
        tools = []
        response_mime_type = "application/json"  # Default to JSON

        if agent_name == "agent1":
            prompt = _build_agent1_prompt(payload)
            # Enable native Google Search for Agent1 and remove JSON enforcement
            search_tool = types.Tool(google_search=types.GoogleSearch())
            tools.append(search_tool)
            response_mime_type = None  # Let the API decide the response type

        elif agent_name == "agent2":
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
        # Only set mime type if it's not None (i.e., for non-tool-using calls)
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

    # Prepare the prompt using the new, structured format.
    prompt_template = '''
# 角色
你是一个专业的“函数工程师”。你的任务是根据“任务简报”和“知识快照”，设计一个完全符合 Google Gemini Function Call 规范的函数声明。
你只输出函数声明，不写真实代码。

# 核心指令
1.  **分析任务**：深入理解“任务简报”中的 `objective`（目标）和 `requirements`（要求）。
2.  **检索现有函数**：检查“知识快照”中的 `function_index`，判断是否有函数能直接或组合使用来满足目标。
3.  **决策**：
    *   **如果找到可用函数**：在 `knowledge_updates` 字段中建议如何使用它，并可以对函数提出优化建议。函数主体部分（name, description等）则简单说明复用情况。
    *   **如果未找到或不完全匹配**：设计一个全新的函数声明。
4.  **输出格式**：必须返回一个单一的、结构严谨的 JSON 对象。不要在 JSON 之外添加任何说明或注释。

# JSON 输出规范
{{
  "name": "函数名，使用蛇形命名法 (snake_case)",
  "description": "对函数功能进行清晰、详尽的描述。说明它的作用、何时使用。",
  "args": {{
    "type": "OBJECT",
    "properties": {{
      "param_name": {{
        "type": "STRING",
        "description": "参数的详细说明"
      }}
    }},
    "required": ["param_name"]
  }},
  "returns": "对函数返回值内容的清晰描述",
  "requirements": [
    "列出运行此函数可能需要的Python库或其他环境依赖，例如 'requests', 'pandas'"
  ],
  "validation": [
    "提供至少一种自动化验证此函数正确性的方案，例如：'doctest: get_weather(\"beijing\") 应该返回包含温度的字符串', '单元测试：使用模拟数据调用并断言结果'"
  ],
  "ownership": "agent2-v1.0",
  "knowledge_updates": [
    {{
      "source": "agent2",
      "category": "lesson",
      "payload": {{ "title": "新学到的经验", "content": "详细内容..." }},
      "notes": "可选的备注"
    }}
  ]
}}

# 输入数据
[任务简报]
{task_brief_json}

[知识快照]
{knowledge_snapshot_json}

[过往产出]
{prior_artifacts_json}
'''

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
    
    prompt_template = '''
# 角色
你是一个专业的“Python工程师”。你的任务是根据“函数声明”，为其编写一个高质量、可直接运行的 Python 实现代码。

# 核心指令
1.  **分析声明**：仔细阅读“函数声明”中的每一个字段，特别是 `name`, `args`, `returns`, 和 `requirements`。
2.  **编写代码**：
    *   编写一个完整的 Python 函数，函数签名必须与 `name` 和 `args` 严格对应。
    *   为函数编写清晰的 Docstring，解释其功能、参数和返回值。
    *   如果声明中包含 `requirements`，请在代码顶部添加必要的 import 语句。
    *   代码应当健壮、可读，并遵循 PEP 8 规范。
3.  **输出格式**：只返回纯粹的 Python 代码块，不要包含任何额外的解释、注释或 markdown 标记。

# 函数声明
{function_spec_json}
'''
    return prompt_template.format(
        function_spec_json=json.dumps(spec, ensure_ascii=False, indent=2)
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
