"""Restricted HTTP client for the configured external backend."""

import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app.config import Settings
from app.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)


class ExternalAPIClient:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = settings.external_api_base_url.rstrip("/") + "/"
        self._api_key = settings.external_api_key
        self._timeout = settings.external_api_timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {settings.external_api_key_header: settings.external_api_key}
        )

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = self._safe_url(path)
        try:
            response = self._session.request(
                method, url, timeout=self._timeout, **kwargs
            )
            logger.info("External API status_code=%s", response.status_code)
            response.raise_for_status()
        except requests.Timeout as exc:
            raise ExternalAPIError(
                "External API không phản hồi đúng thời gian."
            ) from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            messages = {
                400: "Dữ liệu gửi sang backend không hợp lệ.",
                401: "API key không hợp lệ hoặc không có quyền.",
                403: "API key không hợp lệ hoặc không có quyền.",
                404: "Không tìm thấy tài nguyên.",
            }
            if status >= 500:
                message = "External API đang gặp lỗi."
            else:
                message = messages.get(status, "External API từ chối yêu cầu.")
            raise ExternalAPIError(message) from exc
        except requests.RequestException as exc:
            raise ExternalAPIError(
                "Không thể kết nối tới hệ thống bên ngoài."
            ) from exc

        try:
            data = response.json()
        except (requests.JSONDecodeError, ValueError) as exc:
            raise ExternalAPIError(
                "External API trả dữ liệu không đúng định dạng."
            ) from exc
        if not isinstance(data, dict):
            raise ExternalAPIError("External API trả dữ liệu không đúng định dạng.")
        return self._redact_secret(data)

    def _safe_url(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.scheme or parsed.netloc or not path.startswith("/"):
            raise ExternalAPIError("Đường dẫn external API không hợp lệ.")
        return urljoin(self._base_url, path.lstrip("/"))

    def _redact_secret(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._redact_secret(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact_secret(item) for item in value]
        if isinstance(value, str) and self._api_key in value:
            return value.replace(self._api_key, "[REDACTED]")
        return value
