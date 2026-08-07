"""Parser for structured model decisions."""

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from app.core.exceptions import ModelResponseParseError, ToolNotFoundError
from app.tools.registry import has_tool


@dataclass(frozen=True)
class ModelDecision:
    action: Literal["tool_call", "final_answer"]
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def parse_model_response(content: str) -> ModelDecision:
    if not isinstance(content, str):
        raise ModelResponseParseError()
    text = content.strip()
    match = _FENCE.match(text)
    if match:
        text = match.group(1).strip()
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ModelResponseParseError() from exc
    if not isinstance(payload, dict):
        raise ModelResponseParseError()

    action = payload.get("action")
    if action == "final_answer":
        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ModelResponseParseError()
        return ModelDecision(action="final_answer", answer=answer.strip())
    if action == "tool_call":
        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments")
        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            raise ModelResponseParseError()
        if not has_tool(tool_name):
            raise ToolNotFoundError()
        return ModelDecision(
            action="tool_call", tool_name=tool_name, arguments=arguments
        )
    raise ModelResponseParseError()
