"""Cached application dependencies."""

from functools import lru_cache

from app.ai.agent_service import AgentService
from app.ai.llm import get_llm
from app.clients.external_api_client import ExternalAPIClient
from app.config import get_settings
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
    )
