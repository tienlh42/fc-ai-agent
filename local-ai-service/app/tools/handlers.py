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


def get_feedback_list(
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    reason_id: int | None = None,
    guardian_id: int | None = None,
    student_id: int | None = None,
    campus_id: int | None = None,
    feedback_status: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    params = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "priority": priority,
            "reason_id": reason_id,
            "guardian_id": guardian_id,
            "student_id": student_id,
            "campus_id": campus_id,
            "feedback_status": feedback_status,
            "source": source,
        }.items()
        if value is not None
    }
    return _client().get("/feedback/api/feedback/list", params=params)
