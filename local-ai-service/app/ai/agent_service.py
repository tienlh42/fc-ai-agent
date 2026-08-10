"""Bounded structured function-calling loop."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from app.ai.llm import call_model
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.response_parser import parse_model_response
from app.core.exceptions import (
    MaxToolRoundsError,
    ModelResponseParseError,
    OllamaUnavailableError,
    RepeatedToolCallError,
)
from app.tools.executor import ToolExecutor
from app.tools.registry import get_tool_schemas

logger = logging.getLogger(__name__)

FORMAT_REPAIR_PROMPT = (
    "Phản hồi vừa rồi không đúng định dạng. Không trình bày suy luận. "
    "Chỉ trả về đúng một JSON theo schema action đã được cung cấp; "
    "dựa trên kết quả tool mới nhất và không gọi lại tool nếu tool đã trả lỗi."
)


def _enable_thinking_log() -> None:
    """Persist the agent's model/tool decision process to a bounded log file."""
    log_path = Path(__file__).resolve().parents[2] / "logs" / "model-thinking.log"
    if any(
        isinstance(handler, RotatingFileHandler)
        and Path(handler.baseFilename) == log_path
        for handler in logger.handlers
    ):
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)


class AgentService:
    def __init__(
        self,
        llm: Any,
        tool_executor: ToolExecutor,
        max_tool_rounds: int,
        model_caller: Callable[[Any, list[dict[str, str]]], str] = call_model,
        model_timeout: float = 120.0,
        model_max_attempts: int = 3,
    ) -> None:
        self._llm = llm
        self._tool_executor = tool_executor
        self._max_tool_rounds = max_tool_rounds
        self._model_caller = model_caller
        self._model_timeout = model_timeout
        self._model_max_attempts = model_max_attempts

    def _call_model(self, messages: list[dict[str, str]], round_number: int) -> str:
        model_name = getattr(self._llm, "model", type(self._llm).__name__)
        for attempt in range(1, self._model_max_attempts + 1):
            started_at = monotonic()
            logger.info(
                "Model=%s đang xử lý vòng %d (lần thử %d/%d, %d messages, timeout=%.1fs).",
                model_name,
                round_number,
                attempt,
                self._model_max_attempts,
                len(messages),
                self._model_timeout,
            )
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="model-call")
            future = executor.submit(self._model_caller, self._llm, messages)
            try:
                response = future.result(timeout=self._model_timeout)
                logger.info(
                    "Model=%s hoàn tất vòng %d lần thử %d sau %.2fs.",
                    model_name,
                    round_number,
                    attempt,
                    monotonic() - started_at,
                )
                return response
            except FutureTimeoutError as exc:
                future.cancel()
                error: Exception = OllamaUnavailableError(
                    f"Model không phản hồi sau {self._model_timeout:g} giây."
                )
                error.__cause__ = exc
                logger.warning(
                    "Model=%s bị timeout ở vòng %d lần thử %d/%d sau %.2fs.",
                    model_name,
                    round_number,
                    attempt,
                    self._model_max_attempts,
                    monotonic() - started_at,
                )
            except Exception as exc:
                error = exc
                logger.warning(
                    "Model=%s lỗi ở vòng %d lần thử %d/%d sau %.2fs: %s",
                    model_name,
                    round_number,
                    attempt,
                    self._model_max_attempts,
                    monotonic() - started_at,
                    exc,
                )
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            if attempt == self._model_max_attempts:
                logger.error(
                    "Model=%s thất bại sau %d lần thử ở vòng %d.",
                    model_name,
                    self._model_max_attempts,
                    round_number,
                )
                raise error

        raise RuntimeError("Không thể gọi model.")

    def chat(self, message: str) -> dict[str, Any]:
        _enable_thinking_log()
        logger.info("Bắt đầu xử lý yêu cầu bằng model.")
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

        for round_number in range(1, self._max_tool_rounds + 1):
            logger.info(
                "Gọi model (vòng %d/%d).",
                round_number,
                self._max_tool_rounds,
            )
            for format_attempt in range(1, 3):
                raw_response = self._call_model(messages, round_number)
                logger.debug("Phản hồi thô từ model: %r", raw_response)
                try:
                    decision = parse_model_response(raw_response)
                    break
                except ModelResponseParseError:
                    logger.warning(
                        "Model trả sai định dạng ở vòng %d lần %d/2: raw_response=%r",
                        round_number,
                        format_attempt,
                        raw_response[:1000],
                    )
                    if format_attempt == 2:
                        logger.exception(
                            "Không thể parse model response sau khi yêu cầu sửa định dạng."
                        )
                        raise
                    messages.append(
                        {"role": "user", "content": FORMAT_REPAIR_PROMPT}
                    )

            logger.info("Model chọn action=%s ở vòng %d.", decision.action, round_number)
            if decision.action == "final_answer":
                logger.info(
                    "Model hoàn tất sau %d vòng với %d tool call.",
                    round_number,
                    len(tool_calls),
                )
                return {"answer": decision.answer, "tool_calls": tool_calls}

            tool_name = decision.tool_name or ""
            arguments = decision.arguments or {}
            fingerprint = (
                tool_name,
                json.dumps(arguments, sort_keys=True, ensure_ascii=False),
            )
            fingerprints[fingerprint] += 1
            if fingerprints[fingerprint] > 2:
                logger.warning(
                    "Model lặp tool call quá giới hạn: tool=%s arguments=%s.",
                    tool_name,
                    arguments,
                )
                raise RepeatedToolCallError()

            logger.info(
                "Thực thi tool=%s ở vòng %d với arguments=%s.",
                tool_name,
                round_number,
                arguments,
            )
            result = self._tool_executor.execute(tool_name, arguments)
            logger.info(
                "Tool=%s hoàn tất ở vòng %d, success=%s.",
                tool_name,
                round_number,
                result["success"],
            )
            logger.debug("Kết quả tool=%s: %s", tool_name, result)
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

        logger.warning("Model vượt quá giới hạn %d vòng tool call.", self._max_tool_rounds)
        raise MaxToolRoundsError()
