"""Explicit allow-list of tools exposed to the model."""

from app.core.exceptions import ToolNotFoundError
from app.tools.definitions import RegisteredTool
from app.tools.handlers import (
    create_feedback_ticket,
    get_student_detail,
    search_students,
)

TOOL_REGISTRY: dict[str, RegisteredTool] = {
    "search_students": RegisteredTool(
        name="search_students",
        description="Tìm học sinh theo tên hoặc từ khóa.",
        parameters={
            "type": "object",
            "properties": {
                "search": {"type": "string", "minLength": 1, "maxLength": 255},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "required": ["search"],
            "additionalProperties": False,
        },
        handler=search_students,
    ),
    "get_student_detail": RegisteredTool(
        name="get_student_detail",
        description="Lấy thông tin chi tiết của học sinh bằng mã học sinh.",
        parameters={
            "type": "object",
            "properties": {
                "student_number": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 50,
                }
            },
            "required": ["student_number"],
            "additionalProperties": False,
        },
        handler=get_student_detail,
    ),
    "create_feedback_ticket": RegisteredTool(
        name="create_feedback_ticket",
        description="Tạo ticket phản hồi cho một học sinh.",
        parameters={
            "type": "object",
            "properties": {
                "student_number": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 50,
                },
                "title": {"type": "string", "minLength": 1, "maxLength": 255},
                "description": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                },
            },
            "required": ["student_number", "title", "description"],
            "additionalProperties": False,
        },
        handler=create_feedback_ticket,
    ),
}


def get_tool(name: str) -> RegisteredTool:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise ToolNotFoundError() from exc


def get_tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOL_REGISTRY.values()
    ]


def has_tool(name: str) -> bool:
    return name in TOOL_REGISTRY
