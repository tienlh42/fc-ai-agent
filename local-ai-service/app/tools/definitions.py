"""Tool definition type."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
