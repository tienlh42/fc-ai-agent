"""Local AI REST endpoints."""

import requests
from fastapi import APIRouter, Depends

from app.ai.agent_service import AgentService
from app.api.schemas import ChatRequest, ChatResponse, HealthResponse
from app.config import Settings, get_settings
from app.dependencies import get_agent_service

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
