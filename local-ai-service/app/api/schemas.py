"""HTTP request and response schemas."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(max_length=5000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message không được rỗng.")
        return value


class ToolCallInfo(BaseModel):
    name: str
    arguments: dict[str, Any]
    success: bool


class ChatResponse(BaseModel):
    success: bool = True
    answer: str
    tool_calls: list[ToolCallInfo]


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    model: str
    external_api_configured: bool
