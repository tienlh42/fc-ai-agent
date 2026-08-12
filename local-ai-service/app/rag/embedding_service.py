"""Generate vector embeddings through Ollama."""

import logging
from typing import Any

import requests

from app.core.exceptions import OllamaUnavailableError

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float,
        session: requests.Session | None = None,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/api/embed"
        self._model = model
        self._timeout = timeout
        self._session = session or requests.Session()

    def embed(self, texts: str | list[str]) -> list[list[float]]:
        inputs = [texts] if isinstance(texts, str) else texts
        if not inputs:
            return []

        try:
            response = self._session.post(
                self._url,
                json={"model": self._model, "input": inputs},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload: Any = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("Ollama embedding request failed")
            raise OllamaUnavailableError(
                "Không thể tạo embedding bằng Ollama."
            ) from exc

        embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
            raise OllamaUnavailableError("Ollama trả embedding không hợp lệ.")
        return embeddings

    def embed_one(self, text: str) -> list[float]:
        return self.embed(text)[0]
