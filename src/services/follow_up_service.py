"""Follow-up service — manages follow-up alert operations."""

from __future__ import annotations

from typing import Any

from src.aspect_sentiment.follow_up_alerts import (
    list_follow_up_alerts,
    update_follow_up_status,
)


class FollowUpService:
    """Wraps follow-up alert CRUD operations."""

    def list_alerts(
        self,
        *,
        priority: str | None = None,
        status: str | None = None,
        customer_name: str | None = None,
    ) -> dict[str, Any]:
        """Return filtered follow-up alerts."""
        return {
            "alerts": list_follow_up_alerts(
                priority=priority,
                status=status,
                customer_name=customer_name,
            )
        }

    def update_status(self, alert_id: str, status: str) -> dict[str, Any]:
        """Update a follow-up alert status."""
        alert = update_follow_up_status(alert_id, status)
        if alert is None:
            raise ValueError("Follow-up alert not found")
        return {"alert": alert}


follow_up_service = FollowUpService()