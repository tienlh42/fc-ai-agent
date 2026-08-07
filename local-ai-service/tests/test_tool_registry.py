import pytest

from app.core.exceptions import ModelResponseParseError, ToolNotFoundError
from app.tools.registry import get_tool, get_tool_schemas, has_tool
from app.ai.response_parser import parse_model_response


def test_get_existing_tool() -> None:
    assert get_tool("search_students").name == "search_students"
    assert has_tool("get_student_detail")
    assert len(get_tool_schemas()) == 4


def test_get_missing_tool_raises() -> None:
    with pytest.raises(ToolNotFoundError):
        get_tool("unknown")


def test_parser_plain_json() -> None:
    result = parse_model_response('{"action":"final_answer","answer":"Xin chào"}')
    assert result.answer == "Xin chào"


def test_parser_markdown_json() -> None:
    result = parse_model_response(
        '```json\n{"action":"tool_call","tool_name":"search_students",'
        '"arguments":{"search":"An"}}\n```'
    )
    assert result.tool_name == "search_students"


@pytest.mark.parametrize(
    "content",
    ["not-json", '{"answer":"missing action"}', "[]"],
)
def test_parser_rejects_invalid_response(content: str) -> None:
    with pytest.raises(ModelResponseParseError):
        parse_model_response(content)
