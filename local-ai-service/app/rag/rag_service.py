"""Orchestrate document ingestion, retrieval, and answer generation."""

import json
import logging
from typing import Any

import requests

from app.core.exceptions import OllamaUnavailableError
from app.rag.embedding_service import EmbeddingService
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """Bạn là trợ lý trả lời câu hỏi dựa trên tài liệu nội bộ.
Chỉ sử dụng thông tin trong CONTEXT. Nếu context không đủ, hãy nói rõ rằng bạn
không tìm thấy thông tin trong tài liệu. Không tự suy đoán hoặc bịa thông tin.
Trả lời bằng tiếng Việt, ngắn gọn và dễ hiểu. Chỉ điền câu trả lời cuối cùng
vào trường JSON `answer`, không giải thích quá trình suy nghĩ. /no_think"""

RAG_RESPONSE_FORMAT = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
}


class RagService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        retriever: Retriever,
        ollama_base_url: str,
        chat_model: str,
        timeout: float,
        temperature: float,
        chunk_size: int,
        chunk_overlap: int,
        max_output_tokens: int = 256,
        session: requests.Session | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._retriever = retriever
        self._chat_url = f"{ollama_base_url.rstrip('/')}/api/chat"
        self._chat_model = chat_model
        self._timeout = timeout
        self._temperature = temperature
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._max_output_tokens = max_output_tokens
        self._session = session or requests.Session()

    def ingest(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        chunks = self._chunk(text)
        embeddings = self._embedding_service.embed(chunks)
        self._vector_store.replace_document(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
        )
        return len(chunks)

    def query(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        sources = self._retriever.retrieve(question, top_k)
        context = "\n\n".join(
            f"[Nguồn {index}]\n{source['text']}"
            for index, source in enumerate(sources, start=1)
        )
        if not context:
            return {
                "answer": "Không tìm thấy thông tin phù hợp trong tài liệu.",
                "sources": [],
            }

        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\n\n/no_think"
        try:
            response = self._session.post(
                self._chat_url,
                json={
                    "model": self._chat_model,
                    "stream": False,
                    "think": False,
                    "keep_alive": "15m",
                    "format": RAG_RESPONSE_FORMAT,
                    "messages": [
                        {"role": "system", "content": RAG_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "options": {
                        "temperature": self._temperature,
                        "num_predict": self._max_output_tokens,
                    },
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
            answer = payload.get("message", {}).get("content", "").strip()
        except (requests.RequestException, ValueError, AttributeError) as exc:
            logger.exception("Ollama RAG chat request failed")
            raise OllamaUnavailableError() from exc
        if not answer:
            raise OllamaUnavailableError("Ollama trả phản hồi rỗng.")
        try:
            structured_answer = json.loads(answer)
            if isinstance(structured_answer, dict):
                answer = str(structured_answer.get("answer", "")).strip()
        except (json.JSONDecodeError, TypeError):
            pass
        if "</think>" in answer:
            answer = answer.rsplit("</think>", 1)[-1].strip()
        if not answer:
            raise OllamaUnavailableError("Ollama không trả câu trả lời cuối cùng.")
        return {"answer": answer, "sources": sources}

    def _chunk(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + self._chunk_size, len(normalized))
            if end < len(normalized):
                split_at = normalized.rfind(" ", start, end)
                if split_at > start:
                    end = split_at
            chunks.append(normalized[start:end].strip())
            if end >= len(normalized):
                break
            start = max(end - self._chunk_overlap, start + 1)
        return chunks
