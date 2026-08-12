"""ChromaDB-backed storage for document chunks and their embeddings."""

import json
from typing import Any

import chromadb

from app.core.exceptions import VectorStoreError


class VectorStore:
    def __init__(self, host: str, port: int, collection_name: str) -> None:
        try:
            client = chromadb.HttpClient(host=host, port=port)
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorStoreError() from exc

    def replace_document(
        self,
        document_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Số chunk và embedding không khớp.")

        base_metadata = self._normalize_metadata(metadata or {})
        ids = [f"{document_id}:{index}" for index in range(len(chunks))]
        metadatas = [
            {**base_metadata, "document_id": document_id, "chunk_index": index}
            for index in range(len(chunks))
        ]
        try:
            self._collection.delete(where={"document_id": document_id})
            if ids:
                self._collection.upsert(
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
        except Exception as exc:
            raise VectorStoreError("Không thể lưu tài liệu vào ChromaDB.") from exc

    def search(self, embedding: list[float], top_k: int) -> list[dict[str, Any]]:
        try:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError("Không thể tìm kiếm trong ChromaDB.") from exc

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            {
                "id": chunk_id,
                "text": documents[index],
                "metadata": metadatas[index] or {},
                "distance": distances[index],
            }
            for index, chunk_id in enumerate(ids)
        ]

    @staticmethod
    def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            elif value is not None:
                normalized[key] = json.dumps(value, ensure_ascii=False)
        return normalized
