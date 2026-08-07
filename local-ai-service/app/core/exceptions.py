"""Safe, user-facing application exceptions."""


class LocalAIError(Exception):
    error_code = "LOCAL_AI_ERROR"
    default_message = "Đã xảy ra lỗi trong dịch vụ AI."
    status_code = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class OllamaUnavailableError(LocalAIError):
    error_code = "OLLAMA_UNAVAILABLE"
    default_message = "Không thể kết nối tới Ollama."
    status_code = 503


class ModelResponseParseError(LocalAIError):
    error_code = "MODEL_RESPONSE_PARSE_ERROR"
    default_message = "Không thể đọc phản hồi từ mô hình."
    status_code = 502


class ToolNotFoundError(LocalAIError):
    error_code = "TOOL_NOT_FOUND"
    default_message = "Tool không được đăng ký."
    status_code = 400


class ToolValidationError(LocalAIError):
    error_code = "TOOL_VALIDATION_ERROR"
    default_message = "Tham số của tool không hợp lệ."
    status_code = 400


class ToolExecutionError(LocalAIError):
    error_code = "TOOL_EXECUTION_ERROR"
    default_message = "Không thể thực thi tool."
    status_code = 500


class ExternalAPIError(LocalAIError):
    error_code = "EXTERNAL_API_ERROR"
    default_message = "Không thể kết nối tới hệ thống bên ngoài."
    status_code = 502


class MaxToolRoundsError(LocalAIError):
    error_code = "MAX_TOOL_ROUNDS_EXCEEDED"
    default_message = "Đã vượt quá số vòng gọi công cụ cho phép."
    status_code = 502


class RepeatedToolCallError(LocalAIError):
    error_code = "REPEATED_TOOL_CALL"
    default_message = "Model đã yêu cầu lặp lại cùng một công cụ."
    status_code = 502
