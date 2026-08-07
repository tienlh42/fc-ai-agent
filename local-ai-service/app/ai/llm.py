"""Singleton Ollama model and a small model adapter."""

from functools import lru_cache
import logging
from typing import Any

from llama_index.core.llms import ChatMessage
from llama_index.llms.ollama import Ollama

from app.config import get_settings
from app.core.exceptions import OllamaUnavailableError

logger = logging.getLogger(__name__)

# Tuned for this host: i7-12700 (12 physical cores), 32 GB RAM and a 2 GB
# GeForce GT 730. Ollama automatically offloads the layers that fit in VRAM
# and runs the remainder on the CPU.
CONTEXT_WINDOW = 8192
NUM_THREADS = 12
NUM_BATCH = 512
MAX_OUTPUT_TOKENS = 512


@lru_cache(maxsize=1)
def get_llm() -> Ollama:
    settings = get_settings()
    logger.info(
        "Initializing Ollama model=%s context=%s threads=%s batch=%s",
        settings.ollama_model,
        CONTEXT_WINDOW,
        NUM_THREADS,
        NUM_BATCH,
    )
    return Ollama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        request_timeout=settings.ollama_request_timeout,
        temperature=settings.ollama_temperature,
        context_window=CONTEXT_WINDOW,
        additional_kwargs={
            "num_thread": NUM_THREADS,
            "num_batch": NUM_BATCH,
            "num_predict": MAX_OUTPUT_TOKENS,
        },
        keep_alive="15m",
        thinking=False,
    )


def call_model(llm: Any, messages: list[dict[str, str]]) -> str:
    chat_messages = [
        ChatMessage(role=item["role"], content=item["content"]) for item in messages
    ]
    try:
        response = llm.chat(chat_messages)
    except Exception as exc:
        logger.exception("Ollama chat request failed")
        raise OllamaUnavailableError() from exc
    content = response.message.content
    if not isinstance(content, str) or not content.strip():
        raise OllamaUnavailableError("Ollama trả phản hồi rỗng.")
    return content
