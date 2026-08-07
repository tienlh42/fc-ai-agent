"""Validated tool execution."""

import logging
from typing import Any

from jsonschema import ValidationError, validate

from app.core.exceptions import ExternalAPIError, ToolNotFoundError
from app.tools.registry import get_tool

logger = logging.getLogger(__name__)


class ToolExecutor:
    def execute(self, tool_name: str, arguments: dict) -> dict[str, Any]:
        try:
            tool = get_tool(tool_name)
        except ToolNotFoundError:
            return {
                "success": False,
                "tool_name": tool_name,
                "error_code": "TOOL_NOT_FOUND",
                "message": "Tool không được đăng ký.",
            }

        if not isinstance(arguments, dict):
            return self._validation_error(tool_name)

        try:
            validate(instance=arguments, schema=tool.parameters)
            data = tool.handler(**arguments)
            logger.info("Tool name=%s success=true", tool_name)
            return {"success": True, "tool_name": tool_name, "data": data}
        except ValidationError:
            logger.info("Tool name=%s success=false validation_error=true", tool_name)
            return self._validation_error(tool_name)
        except ExternalAPIError as exc:
            logger.warning("Tool name=%s success=false external_error=true", tool_name)
            return {
                "success": False,
                "tool_name": tool_name,
                "error_code": exc.error_code,
                "message": exc.message,
            }
        except Exception:
            # Do not log the raw exception because a third-party error could
            # accidentally include credentials or sensitive response content.
            logger.error("Tool name=%s success=false internal_error=true", tool_name)
            return {
                "success": False,
                "tool_name": tool_name,
                "error_code": "TOOL_EXECUTION_ERROR",
                "message": "Không thể thực thi tool.",
            }

    @staticmethod
    def _validation_error(tool_name: str) -> dict[str, Any]:
        return {
            "success": False,
            "tool_name": tool_name,
            "error_code": "TOOL_VALIDATION_ERROR",
            "message": "Tham số của tool không hợp lệ.",
        }
