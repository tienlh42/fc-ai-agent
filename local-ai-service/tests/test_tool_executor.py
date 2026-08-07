from unittest.mock import Mock

import pytest
import requests

from app.clients.external_api_client import ExternalAPIClient
from app.config import Settings
from app.core.exceptions import ExternalAPIError
from app.tools.definitions import RegisteredTool
from app.tools.executor import ToolExecutor
from app.tools.registry import TOOL_REGISTRY


def make_settings() -> Settings:
    return Settings(
        app_host="127.0.0.1",
        app_port=8010,
        log_level="INFO",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen3:8b",
        ollama_request_timeout=120,
        ollama_temperature=0.1,
        max_tool_rounds=5,
        external_api_base_url="http://localhost:8080/",
        external_api_key="test-secret",
        external_api_key_header="Api-Key",
        external_api_timeout=15,
    )


def test_executor_executes_valid_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = Mock(return_value={"items": []})
    tool = RegisteredTool(
        name="test_tool",
        description="test",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        handler=handler,
    )
    monkeypatch.setitem(TOOL_REGISTRY, "test_tool", tool)
    result = ToolExecutor().execute("test_tool", {"name": "An"})
    assert result["success"] is True
    handler.assert_called_once_with(name="An")


@pytest.mark.parametrize("arguments", [{}, {"search": "An", "extra": True}])
def test_executor_rejects_invalid_arguments(arguments: dict) -> None:
    result = ToolExecutor().execute("search_students", arguments)
    assert result["success"] is False
    assert result["error_code"] == "TOOL_VALIDATION_ERROR"


def test_executor_rejects_unknown_tool() -> None:
    result = ToolExecutor().execute("unknown", {})
    assert result["error_code"] == "TOOL_NOT_FOUND"


def test_external_client_adds_api_key_and_redacts_response() -> None:
    session = Mock()
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"value": "test-secret"}
    session.request.return_value = response
    client = ExternalAPIClient(make_settings(), session=session)

    result = client.get("/api/students")

    assert session.headers.update.call_args.args[0] == {"Api-Key": "test-secret"}
    assert result == {"value": "[REDACTED]"}
    assert session.request.call_args.kwargs["timeout"] == 15


def test_external_client_converts_timeout() -> None:
    session = Mock()
    session.request.side_effect = requests.Timeout()
    client = ExternalAPIClient(make_settings(), session=session)
    with pytest.raises(ExternalAPIError, match="đúng thời gian"):
        client.get("/api/students")
