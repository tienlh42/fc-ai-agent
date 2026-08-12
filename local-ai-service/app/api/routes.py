"""Local AI REST endpoints."""

import json

import requests
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.ai.agent_service import AgentService
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    RagIngestRequest,
    RagIngestResponse,
    RagFileIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
)
from app.config import Settings, get_settings
from app.core.exceptions import DocumentFileError
from app.dependencies import get_agent_service, get_document_storage, get_rag_service
from app.rag.document_storage import DocumentStorage
from app.rag.rag_service import RagService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    ollama_ok = False
    try:
        response = requests.get(
            f"{settings.ollama_base_url.rstrip('/')}/api/tags",
            timeout=min(settings.ollama_request_timeout, 5),
        )
        response.raise_for_status()
        ollama_ok = True
    except requests.RequestException:
        pass
    return HealthResponse(
        status="healthy" if ollama_ok else "degraded",
        ollama=ollama_ok,
        model=settings.ollama_model,
        external_api_configured=bool(
            settings.external_api_base_url and settings.external_api_key
        ),
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    agent: AgentService = Depends(get_agent_service),
) -> ChatResponse:
    result = agent.chat(request.message)
    return ChatResponse(success=True, **result)


@router.post("/rag/ingest", response_model=RagIngestResponse)
def rag_ingest(
    request: RagIngestRequest,
    rag: RagService = Depends(get_rag_service),
) -> RagIngestResponse:
    chunks = sum(
        rag.ingest(document.document_id, document.text, document.metadata)
        for document in request.documents
    )
    return RagIngestResponse(documents=len(request.documents), chunks=chunks)


@router.post("/rag/ingest/file", response_model=RagFileIngestResponse)
def rag_ingest_file(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    rag: RagService = Depends(get_rag_service),
    storage: DocumentStorage = Depends(get_document_storage),
) -> RagFileIngestResponse:
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError as exc:
        raise DocumentFileError("metadata phải là JSON hợp lệ.") from exc
    if not isinstance(parsed_metadata, dict):
        raise DocumentFileError("metadata phải là một JSON object.")

    stored = storage.save_and_extract(
        stream=file.file,
        original_filename=file.filename or "",
        document_id=document_id,
    )
    chunk_metadata = {
        **parsed_metadata,
        "filename": stored["original_filename"],
        "content_type": stored["content_type"],
    }
    chunks = rag.ingest(stored["document_id"], stored["text"], chunk_metadata)
    return RagFileIngestResponse(
        document_id=stored["document_id"],
        filename=stored["original_filename"],
        size=stored["size"],
        chunks=chunks,
    )


@router.get("/rag/documents/{document_id}/file")
def rag_document_file(
    document_id: str,
    storage: DocumentStorage = Depends(get_document_storage),
) -> FileResponse:
    stored = storage.get(document_id)
    return FileResponse(
        path=stored["path"],
        filename=stored["original_filename"],
        media_type=stored["content_type"],
    )


@router.post("/rag/query", response_model=RagQueryResponse)
def rag_query(
    request: RagQueryRequest,
    rag: RagService = Depends(get_rag_service),
) -> RagQueryResponse:
    result = rag.query(request.question, request.top_k)
    return RagQueryResponse(success=True, **result)
