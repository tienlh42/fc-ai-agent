"""Persist uploaded source documents and extract text for RAG ingestion."""

import hashlib
import io
import json
from pathlib import Path
import re
import shutil
from typing import BinaryIO, Any
import uuid

from docx import Document
from pypdf import PdfReader

from app.core.exceptions import DocumentFileError

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentStorage:
    def __init__(self, storage_dir: str, max_file_size: int) -> None:
        self._root = Path(storage_dir).resolve()
        self._max_file_size = max_file_size
        self._root.mkdir(parents=True, exist_ok=True)

    def save_and_extract(
        self,
        stream: BinaryIO,
        original_filename: str,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        suffix = Path(original_filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise DocumentFileError(
                "Chỉ hỗ trợ file .txt, .md, .pdf và .docx."
            )

        resolved_document_id = (document_id or str(uuid.uuid4())).strip()
        if not resolved_document_id or len(resolved_document_id) > 200:
            raise DocumentFileError("document_id không hợp lệ.")

        directory = self._document_directory(resolved_document_id)
        directory.mkdir(parents=True, exist_ok=True)
        stored_path = directory / f"source{suffix}"
        temporary_path = directory / f"upload-{uuid.uuid4().hex}.tmp"
        size = 0
        try:
            with temporary_path.open("wb") as target:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > self._max_file_size:
                        raise DocumentFileError(
                            f"File vượt quá giới hạn {self._max_file_size // (1024 * 1024)} MB."
                        )
                    target.write(chunk)
            if size == 0:
                raise DocumentFileError("File tải lên không có nội dung.")

            text = self._extract_text(temporary_path, suffix)
            if not text.strip():
                raise DocumentFileError("Không trích xuất được nội dung từ file.")

            for old_source in directory.glob("source.*"):
                if old_source != stored_path:
                    old_source.unlink(missing_ok=True)
            temporary_path.replace(stored_path)
            safe_name = self._safe_filename(original_filename, suffix)
            manifest = {
                "document_id": resolved_document_id,
                "original_filename": safe_name,
                "stored_filename": stored_path.name,
                "content_type": self._content_type(suffix),
                "size": size,
            }
            (directory / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            return {**manifest, "text": text, "stored_path": str(stored_path)}
        except DocumentFileError:
            temporary_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temporary_path.unlink(missing_ok=True)
            raise DocumentFileError("Không thể xử lý file tải lên.") from exc

    def get(self, document_id: str) -> dict[str, Any]:
        directory = self._document_directory(document_id)
        manifest_path = directory / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            stored_path = (directory / manifest["stored_filename"]).resolve()
        except (OSError, KeyError, ValueError, TypeError) as exc:
            raise DocumentFileError("Không tìm thấy file tài liệu.", status_code=404) from exc
        if stored_path.parent != directory or not stored_path.is_file():
            raise DocumentFileError("Không tìm thấy file tài liệu.", status_code=404)
        return {**manifest, "path": str(stored_path)}

    def delete(self, document_id: str) -> None:
        directory = self._document_directory(document_id)
        if directory.is_dir():
            shutil.rmtree(directory)

    def _document_directory(self, document_id: str) -> Path:
        digest = hashlib.sha256(document_id.encode("utf-8")).hexdigest()
        directory = (self._root / digest).resolve()
        if directory.parent != self._root:
            raise DocumentFileError("document_id không hợp lệ.")
        return directory

    @staticmethod
    def _extract_text(path: Path, suffix: str) -> str:
        data = path.read_bytes()
        if suffix in {".txt", ".md"}:
            for encoding in ("utf-8-sig", "cp1258", "latin-1"):
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix == ".docx":
            document = Document(io.BytesIO(data))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        raise DocumentFileError("Định dạng file không được hỗ trợ.")

    @staticmethod
    def _safe_filename(filename: str, suffix: str) -> str:
        name = Path(filename).name
        safe_name = SAFE_FILENAME_PATTERN.sub("_", name).strip("._")
        return safe_name or f"document{suffix}"

    @staticmethod
    def _content_type(suffix: str) -> str:
        return {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }[suffix]
