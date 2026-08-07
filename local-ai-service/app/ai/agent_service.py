"""Bounded structured function-calling loop."""

from collections import Counter
import json
import logging
from typing import Any, Callable

from app.ai.llm import call_model
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.response_parser import parse_model_response
from app.core.exceptions import MaxToolRoundsError, RepeatedToolCallError
from app.tools.executor import ToolExecutor
from app.tools.registry import get_tool_schemas

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(
        self,
        llm: Any,
        tool_executor: ToolExecutor,
        max_tool_rounds: int,
        model_caller: Callable[[Any, list[dict[str, str]]], str] = call_model,
    ) -> None:
        self._llm = llm
        self._tool_executor = tool_executor
        self._max_tool_rounds = max_tool_rounds
        self._model_caller = model_caller

    def chat(self, message: str) -> dict[str, Any]:
        schemas = json.dumps(get_tool_schemas(), ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\nDanh sách tool và schema:\n{schemas}",
            },
            {"role": "user", "content": message},
        ]
        tool_calls: list[dict[str, Any]] = []
        fingerprints: Counter[tuple[str, str]] = Counter()

        for _ in range(self._max_tool_rounds):
            raw_response = self._model_caller(self._llm, messages)
            try:
                decision = parse_model_response(raw_response)
            except Exception:
                logger.warning("Không thể parse model response.")
                raise

            if decision.action == "final_answer":
                return {"answer": decision.answer, "tool_calls": tool_calls}

            tool_name = decision.tool_name or ""
            arguments = decision.arguments or {}
            fingerprint = (
                tool_name,
                json.dumps(arguments, sort_keys=True, ensure_ascii=False),
            )
            fingerprints[fingerprint] += 1
            if fingerprints[fingerprint] > 2:
                raise RepeatedToolCallError()

            result = self._tool_executor.execute(tool_name, arguments)
            tool_calls.append(
                {
                    "name": tool_name,
                    "arguments": arguments,
                    "success": result["success"],
                }
            )
            normalized = {
                "action": "tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
            }
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(normalized, ensure_ascii=False),
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        raise MaxToolRoundsError()
