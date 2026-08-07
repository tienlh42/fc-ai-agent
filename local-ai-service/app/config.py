"""Environment-based application settings."""

from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} phải là một số nguyên hợp lệ.") from exc


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} phải là một số hợp lệ.") from exc


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    log_level: str
    ollama_base_url: str
    ollama_model: str
    ollama_request_timeout: float
    ollama_temperature: float
    max_tool_rounds: int
    external_api_base_url: str
    external_api_key: str
    external_api_key_header: str
    external_api_timeout: float

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        settings = cls(
            app_host=os.getenv("APP_HOST", "127.0.0.1").strip(),
            app_port=_read_int("APP_PORT", 8010),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            ollama_base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ).strip(),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b").strip(),
            ollama_request_timeout=_read_float("OLLAMA_REQUEST_TIMEOUT", 120),
            ollama_temperature=_read_float("OLLAMA_TEMPERATURE", 0.1),
            max_tool_rounds=_read_int("MAX_TOOL_ROUNDS", 5),
            external_api_base_url=os.getenv("EXTERNAL_API_BASE_URL", "").strip(),
            external_api_key=os.getenv("EXTERNAL_API_KEY", "").strip(),
            external_api_key_header=os.getenv(
                "EXTERNAL_API_KEY_HEADER", "Api-Key"
            ).strip(),
            external_api_timeout=_read_float("EXTERNAL_API_TIMEOUT", 15),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not 1 <= self.app_port <= 65535:
            raise ValueError("APP_PORT phải nằm trong khoảng 1 đến 65535.")
        if self.ollama_request_timeout <= 0:
            raise ValueError("OLLAMA_REQUEST_TIMEOUT phải lớn hơn 0.")
        if self.external_api_timeout <= 0:
            raise ValueError("EXTERNAL_API_TIMEOUT phải lớn hơn 0.")
        if not 1 <= self.max_tool_rounds <= 10:
            raise ValueError("MAX_TOOL_ROUNDS phải nằm trong khoảng 1 đến 10.")
        if not self.ollama_base_url:
            raise ValueError("OLLAMA_BASE_URL không được rỗng.")
        if not self.ollama_model:
            raise ValueError("OLLAMA_MODEL không được rỗng.")
        if not self.external_api_base_url:
            raise ValueError("EXTERNAL_API_BASE_URL không được rỗng.")
        if not self.external_api_key:
            # Never include the secret value in validation messages.
            raise ValueError("EXTERNAL_API_KEY không được rỗng.")
        if not self.external_api_key_header:
            raise ValueError("EXTERNAL_API_KEY_HEADER không được rỗng.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
