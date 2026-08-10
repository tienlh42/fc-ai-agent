import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.ai.agent_service import AgentService
from app.core.exceptions import MaxToolRoundsError, RepeatedToolCallError
from app.dependencies import get_agent_service
from app.main import app


def sequence_caller(responses: list[str], seen: list | None = None):
    iterator = iter(responses)

    def caller(llm, messages):
        if seen is not None:
            seen.append(messages.copy())
        return next(iterator)

    return caller


def test_loop_stops_on_final_answer() -> None:
    agent = AgentService(
        llm=Mock(),
        tool_executor=Mock(),
        max_tool_rounds=5,
        model_caller=sequence_caller(
            ['{"action":"final_answer","answer":"Xin chào"}']
        ),
    )
    assert agent.chat("Chào") == {"answer": "Xin chào", "tool_calls": []}


def test_loop_repairs_non_json_model_response_once() -> None:
    seen: list = []
    agent = AgentService(
        llm=Mock(),
        tool_executor=Mock(),
        max_tool_rounds=5,
        model_caller=sequence_caller(
            [
                "I need to think about this first.",
                '{"action":"final_answer","answer":"Xin chào"}',
            ],
            seen,
        ),
    )

    assert agent.chat("Chào") == {"answer": "Xin chào", "tool_calls": []}
    assert seen[1][-1]["role"] == "user"
    assert "Chỉ trả về đúng một JSON" in seen[1][-1]["content"]


def test_loop_executes_tool_and_returns_result_to_model() -> None:
    executor = Mock()
    executor.execute.return_value = {
        "success": True,
        "tool_name": "search_students",
        "data": {"items": [{"name": "An"}]},
    }
    seen: list = []
    agent = AgentService(
        llm=Mock(),
        tool_executor=executor,
        max_tool_rounds=5,
        model_caller=sequence_caller(
            [
                json.dumps(
                    {
                        "action": "tool_call",
                        "tool_name": "search_students",
                        "arguments": {"search": "An"},
                    }
                ),
                '{"action":"final_answer","answer":"Đã tìm thấy An"}',
            ],
            seen,
        ),
    )
    result = agent.chat("Tìm An")
    assert result["tool_calls"][0]["success"] is True
    assert any(
        message["role"] == "tool" and "items" in message["content"]
        for message in seen[1]
    )


def test_loop_stops_at_max_rounds() -> None:
    tool_call = (
        '{"action":"tool_call","tool_name":"search_students",'
        '"arguments":{"search":"An"}}'
    )
    executor = Mock()
    executor.execute.return_value = {"success": True, "data": {}}
    agent = AgentService(
        llm=Mock(),
        tool_executor=executor,
        max_tool_rounds=2,
        model_caller=sequence_caller([tool_call, tool_call]),
    )
    with pytest.raises(MaxToolRoundsError):
        agent.chat("Tìm An")


def test_loop_detects_repeated_tool_call() -> None:
    tool_call = (
        '{"action":"tool_call","tool_name":"search_students",'
        '"arguments":{"search":"An"}}'
    )
    executor = Mock()
    executor.execute.return_value = {"success": True, "data": {}}
    agent = AgentService(
        llm=Mock(),
        tool_executor=executor,
        max_tool_rounds=5,
        model_caller=sequence_caller([tool_call] * 3),
    )
    with pytest.raises(RepeatedToolCallError):
        agent.chat("Tìm An")


def test_chat_api_response_schema() -> None:
    fake_agent = Mock()
    fake_agent.chat.return_value = {
        "answer": "Tôi tìm thấy An.",
        "tool_calls": [
            {
                "name": "search_students",
                "arguments": {"search": "An"},
                "success": True,
            }
        ],
    }
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    try:
        response = TestClient(app).post(
            "/api/v1/chat", json={"message": "Tìm học sinh An"}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["tool_calls"][0]["name"] == "search_students"


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({"prompt": "Tìm học sinh An"}, "Tìm học sinh An"),
        ({"query": "Tìm học sinh Bình"}, "Tìm học sinh Bình"),
        ({"input": "Tìm học sinh Chi"}, "Tìm học sinh Chi"),
        (
            {"messages": [{"role": "user", "content": "Tìm học sinh Dũng"}]},
            "Tìm học sinh Dũng",
        ),
        ("Tìm học sinh Em", "Tìm học sinh Em"),
    ],
)
def test_chat_api_accepts_common_payload_shapes(
    payload: object, expected_message: str
) -> None:
    fake_agent = Mock()
    fake_agent.chat.return_value = {"answer": "OK", "tool_calls": []}
    app.dependency_overrides[get_agent_service] = lambda: fake_agent
    try:
        response = TestClient(app).post("/api/v1/chat", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    fake_agent.chat.assert_called_once_with(expected_message)


@pytest.mark.parametrize("message", ["", " " * 3, "x" * 5001])
def test_chat_api_validates_message(message: str) -> None:
    app.dependency_overrides[get_agent_service] = lambda: Mock()
    try:
        response = TestClient(app).post("/api/v1/chat", json={"message": message})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_ERROR"
