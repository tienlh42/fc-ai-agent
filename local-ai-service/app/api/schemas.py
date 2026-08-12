"""HTTP request and response schemas."""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ChatRequest(BaseModel):
    message: str = Field(max_length=5000)

    @model_validator(mode="before")
    @classmethod
    def normalize_message_payload(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"message": value}
        if not isinstance(value, dict) or "message" in value:
            return value

        for key in ("prompt", "query", "input"):
            if isinstance(value.get(key), str):
                return {**value, "message": value[key]}

        messages = value.get("messages")
        if isinstance(messages, list):
            for item in reversed(messages):
                if (
                    isinstance(item, dict)
                    and item.get("role") == "user"
                    and isinstance(item.get("content"), str)
                ):
                    return {**value, "message": item["content"]}

        return value

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


class RagDocument(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIngestRequest(BaseModel):
    documents: list[RagDocument] = Field(min_length=1, max_length=100)


class RagIngestResponse(BaseModel):
    success: bool = True
    documents: int
    chunks: int


class RagFileIngestResponse(BaseModel):
    success: bool = True
    document_id: str
    filename: str
    size: int
    chunks: int


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSource(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float


class RagQueryResponse(BaseModel):
    success: bool = True
    answer: str
    sources: list[RagSource]
