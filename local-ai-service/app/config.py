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
    embedding_model: str = "embeddinggemma"
    chroma_host: str = "127.0.0.1"
    chroma_port: int = 8000
    chroma_collection: str = "local_documents"
    rag_top_k: int = 5
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    rag_max_output_tokens: int = 256
    document_storage_dir: str = "/data/documents"
    document_max_file_size_mb: int = 20

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
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "embeddinggemma"
            ).strip(),
            chroma_host=os.getenv("CHROMA_HOST", "127.0.0.1").strip(),
            chroma_port=_read_int("CHROMA_PORT", 8000),
            chroma_collection=os.getenv(
                "CHROMA_COLLECTION", "local_documents"
            ).strip(),
            rag_top_k=_read_int("RAG_TOP_K", 5),
            rag_chunk_size=_read_int("RAG_CHUNK_SIZE", 1000),
            rag_chunk_overlap=_read_int("RAG_CHUNK_OVERLAP", 150),
            rag_max_output_tokens=_read_int("RAG_MAX_OUTPUT_TOKENS", 256),
            document_storage_dir=os.getenv(
                "DOCUMENT_STORAGE_DIR", "/data/documents"
            ).strip(),
            document_max_file_size_mb=_read_int("DOCUMENT_MAX_FILE_SIZE_MB", 20),
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
        if not self.embedding_model:
            raise ValueError("EMBEDDING_MODEL không được rỗng.")
        if not self.chroma_host or not self.chroma_collection:
            raise ValueError("Cấu hình ChromaDB không được rỗng.")
        if not 1 <= self.chroma_port <= 65535:
            raise ValueError("CHROMA_PORT phải nằm trong khoảng 1 đến 65535.")
        if not 1 <= self.rag_top_k <= 20:
            raise ValueError("RAG_TOP_K phải nằm trong khoảng 1 đến 20.")
        if self.rag_chunk_size < 100:
            raise ValueError("RAG_CHUNK_SIZE phải ít nhất là 100.")
        if not 0 <= self.rag_chunk_overlap < self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP phải nhỏ hơn RAG_CHUNK_SIZE.")
        if not 1 <= self.rag_max_output_tokens <= 2048:
            raise ValueError("RAG_MAX_OUTPUT_TOKENS phải nằm trong khoảng 1 đến 2048.")
        if not self.document_storage_dir:
            raise ValueError("DOCUMENT_STORAGE_DIR không được rỗng.")
        if not 1 <= self.document_max_file_size_mb <= 200:
            raise ValueError("DOCUMENT_MAX_FILE_SIZE_MB phải từ 1 đến 200.")
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
