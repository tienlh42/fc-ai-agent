"""Singleton Ollama model and a small model adapter."""

from functools import lru_cache
import logging
from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.llms.ollama import Ollama

from app.config import get_settings
from app.core.exceptions import OllamaUnavailableError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> Ollama:
    settings = get_settings()
    logger.info("Initializing Ollama model=%s", settings.ollama_model)
    return Ollama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout,
        temperature=settings.ollama_temperature,
    )


def call_model(llm: Any, messages: list[dict[str, str]]) -> str:
    chat_messages = [
        ChatMessage(role=item["role"], content=item["content"]) for item in messages
    ]
    try:
        response = llm.chat(chat_messages)
    except Exception as exc:
        raise OllamaUnavailableError() from exc
    content = response.message.content
    if not isinstance(content, str) or not content.strip():
        raise OllamaUnavailableError("Ollama trả phản hồi rỗng.")
    return content
