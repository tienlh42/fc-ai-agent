"""Embed a question and retrieve the closest chunks."""

from typing import Any

from app.rag.embedding_service import EmbeddingService
from app.rag.vector_store import VectorStore


class Retriever:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        default_top_k: int = 5,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_top_k = default_top_k

    def retrieve(
        self, question: str, top_k: int | None = None
    ) -> list[dict[str, Any]]:
        query_embedding = self._embedding_service.embed_one(question)
        return self._vector_store.search(
            query_embedding,
            top_k if top_k is not None else self._default_top_k,
        )
