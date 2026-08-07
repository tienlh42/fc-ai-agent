"""Handlers with fixed external API routes."""

from typing import Any
from urllib.parse import quote

from app.clients.external_api_client import ExternalAPIClient


def _client() -> ExternalAPIClient:
    # Local import keeps dependency construction lazy and avoids import cycles.
    from app.dependencies import get_external_api_client

    return get_external_api_client()


def search_students(search: str, limit: int = 10) -> dict[str, Any]:
    return _client().get(
        "/api/students",
        params={"search": search, "limit": limit},
    )


def get_student_detail(student_number: str) -> dict[str, Any]:
    safe_student_number = quote(student_number, safe="")
    return _client().get(f"/api/students/{safe_student_number}")


def create_feedback_ticket(
    student_number: str,
    title: str,
    description: str,
) -> dict[str, Any]:
    # Production should require explicit user confirmation before write operations.
    return _client().post(
        "/api/feedback/tickets",
        payload={
            "student_number": student_number,
            "title": title,
            "description": description,
        },
    )
