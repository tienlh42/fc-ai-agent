"""Cached application dependencies."""

from functools import lru_cache

from app.ai.agent_service import AgentService
from app.ai.llm import get_llm
from app.clients.external_api_client import ExternalAPIClient
from app.config import get_settings
from app.rag.embedding_service import EmbeddingService
from app.rag.document_storage import DocumentStorage
from app.rag.rag_service import RagService
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.tools.executor import ToolExecutor


@lru_cache(maxsize=1)
def get_external_api_client() -> ExternalAPIClient:
    return ExternalAPIClient(get_settings())


@lru_cache(maxsize=1)
def get_tool_executor() -> ToolExecutor:
    return ToolExecutor()


@lru_cache(maxsize=1)
def get_agent_service() -> AgentService:
    settings = get_settings()
    return AgentService(
        llm=get_llm(),
        tool_executor=get_tool_executor(),
        max_tool_rounds=settings.max_tool_rounds,
        model_timeout=settings.ollama_request_timeout,
    )


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model,
        timeout=settings.ollama_request_timeout,
    )


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    settings = get_settings()
    return VectorStore(
        host=settings.chroma_host,
        port=settings.chroma_port,
        collection_name=settings.chroma_collection,
    )


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    settings = get_settings()
    return Retriever(
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        default_top_k=settings.rag_top_k,
    )


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    settings = get_settings()
    return RagService(
        embedding_service=get_embedding_service(),
        vector_store=get_vector_store(),
        retriever=get_retriever(),
        ollama_base_url=settings.ollama_base_url,
        chat_model=settings.ollama_model,
        timeout=settings.ollama_request_timeout,
        temperature=settings.ollama_temperature,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        max_output_tokens=settings.rag_max_output_tokens,
    )


@lru_cache(maxsize=1)
def get_document_storage() -> DocumentStorage:
    settings = get_settings()
    return DocumentStorage(
        storage_dir=settings.document_storage_dir,
        max_file_size=settings.document_max_file_size_mb * 1024 * 1024,
    )
