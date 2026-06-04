"""
Bulk event check-in upload: classification, validation, processing, and Redis job state.

Used by POST /v1/events/academy/event/<event_id>/checkin/bulk and GET .../bulk/<job_id>.
"""
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from capyc.rest_framework.exceptions import ValidationException
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from breathecode.events.models import DONE, Event, EventCheckin

logger = logging.getLogger(__name__)


class BulkEventCheckinManager:
    """Manager for bulk event check-in import."""

    class Scenario(str, Enum):
        NEW_CHECKIN = "NEW_CHECKIN"
        ALREADY_REGISTERED = "ALREADY_REGISTERED"
        ALREADY_ATTENDED = "ALREADY_ATTENDED"

    KEY_PREFIX = "bulk_event_checkin_upload"
    TTL_SECONDS = 24 * 60 * 60

    @staticmethod
    def classify_row(event_id: int, email: str) -> "BulkEventCheckinManager.Scenario":
        email = (email or "").strip().lower()
        if not email:
            raise ValidationException("Email is required", slug="email-required", code=400)

        checkin = EventCheckin.objects.filter(email__iexact=email, event_id=event_id).first()
        if checkin is None:
            return BulkEventCheckinManager.Scenario.NEW_CHECKIN
        if checkin.status == DONE or checkin.attended_at is not None:
            return BulkEventCheckinManager.Scenario.ALREADY_ATTENDED
        return BulkEventCheckinManager.Scenario.ALREADY_REGISTERED

    @staticmethod
    def _row_result(
        classification: "BulkEventCheckinManager.Scenario",
        row_data: dict,
        status: str,
        message: Optional[str] = None,
        event_checkin_id: Optional[int] = None,
        slug: Optional[str] = None,
        marketing_status: Optional[str] = None,
    ) -> dict:
        email = (row_data.get("email") or "").strip().lower()
        result = {
            "classification": classification.value,
            "email": email,
            "first_name": row_data.get("first_name"),
            "last_name": row_data.get("last_name"),
            "status": status,
            "message": message,
            "event_checkin_id": event_checkin_id,
            "slug": slug,
        }
        if marketing_status is not None:
            result["marketing_status"] = marketing_status
        return result

    @staticmethod
    def _parse_attended_at(value) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        parsed = parse_datetime(str(value))
        return parsed

    @staticmethod
    def validate_row(event_id: int, academy_id: int, row_data: dict) -> dict:
        email = (row_data.get("email") or "").strip().lower()
        if not email:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message="Email is required",
                slug="email-required",
            )

        event = Event.objects.filter(id=event_id, academy_id=academy_id).first()
        if not event:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message="Event not found or does not belong to this academy",
                slug="event-not-found",
            )

        try:
            classification = BulkEventCheckinManager.classify_row(event_id, email)
        except ValidationException as e:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message=str(getattr(e, "detail", e)),
                slug=getattr(e, "slug", None) or "email-required",
            )

        attended = bool(row_data.get("attended"))

        if classification == BulkEventCheckinManager.Scenario.ALREADY_ATTENDED and not attended:
            return BulkEventCheckinManager._row_result(
                classification, row_data, "skipped", message="Already attended"
            )

        if classification == BulkEventCheckinManager.Scenario.ALREADY_REGISTERED and not attended:
            return BulkEventCheckinManager._row_result(
                classification, row_data, "skipped", message="Already registered for this event"
            )

        if classification == BulkEventCheckinManager.Scenario.ALREADY_REGISTERED and attended:
            return BulkEventCheckinManager._row_result(classification, row_data, "updated")

        if classification == BulkEventCheckinManager.Scenario.NEW_CHECKIN:
            return BulkEventCheckinManager._row_result(classification, row_data, "created")

        return BulkEventCheckinManager._row_result(classification, row_data, "skipped")

    @staticmethod
    def process_row(
        event_id: int,
        academy_id: int,
        row_data: dict,
        run_marketing: bool = False,
    ) -> dict:
        from breathecode.events import actions as events_actions
        from breathecode.events import tasks as events_tasks

        email = (row_data.get("email") or "").strip().lower()
        if not email:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message="Email is required",
                slug="email-required",
            )

        event = Event.objects.filter(id=event_id, academy_id=academy_id).select_related("academy").first()
        if not event:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message="Event not found or does not belong to this academy",
                slug="event-not-found",
            )

        try:
            classification = BulkEventCheckinManager.classify_row(event_id, email)
        except ValidationException as e:
            return BulkEventCheckinManager._row_result(
                BulkEventCheckinManager.Scenario.NEW_CHECKIN,
                row_data,
                "failed",
                message=str(getattr(e, "detail", e)),
                slug=getattr(e, "slug", None) or "email-required",
            )

        attended = bool(row_data.get("attended"))
        attended_at = BulkEventCheckinManager._parse_attended_at(row_data.get("attended_at"))

        if classification == BulkEventCheckinManager.Scenario.ALREADY_ATTENDED and not attended:
            checkin = EventCheckin.objects.filter(email__iexact=email, event_id=event_id).first()
            return BulkEventCheckinManager._row_result(
                classification,
                row_data,
                "skipped",
                message="Already attended",
                event_checkin_id=checkin.id if checkin else None,
            )

        if classification == BulkEventCheckinManager.Scenario.ALREADY_REGISTERED and not attended:
            checkin = EventCheckin.objects.filter(email__iexact=email, event_id=event_id).first()
            return BulkEventCheckinManager._row_result(
                classification,
                row_data,
                "skipped",
                message="Already registered for this event",
                event_checkin_id=checkin.id if checkin else None,
            )

        try:
            checkin, created, attended_updated = events_actions.upsert_event_checkin(
                event=event,
                email=email,
                attended=attended,
                attended_at=attended_at,
                utm_source=row_data.get("utm_source"),
                utm_medium=row_data.get("utm_medium"),
                utm_campaign=row_data.get("utm_campaign"),
                utm_url=row_data.get("utm_url"),
            )
        except Exception as e:
            logger.exception("upsert_event_checkin failed for email=%s", email)
            return BulkEventCheckinManager._row_result(
                classification,
                row_data,
                "failed",
                message=str(e),
                slug="unexpected-error",
            )

        if created:
            row_status = "created"
        elif attended_updated or (attended and classification == BulkEventCheckinManager.Scenario.ALREADY_REGISTERED):
            row_status = "updated"
        else:
            row_status = "skipped"

        marketing_status = None
        if run_marketing and row_status in ("created", "updated"):
            events_tasks.run_event_checkin_marketing_task.delay(
                event_id=event.id,
                email=email,
                first_name=row_data.get("first_name") or "",
                last_name=row_data.get("last_name") or "",
                utm_source=row_data.get("utm_source"),
                campaign=row_data.get("utm_campaign"),
            )
            marketing_status = "queued"

        return BulkEventCheckinManager._row_result(
            classification,
            row_data,
            row_status,
            event_checkin_id=checkin.id,
            marketing_status=marketing_status,
        )

    @staticmethod
    def get_job_key(job_id: str) -> str:
        return f"{BulkEventCheckinManager.KEY_PREFIX}:{job_id}"

    @staticmethod
    def get_job_state(job_id: str) -> Optional[dict]:
        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return None
            return cache.get(BulkEventCheckinManager.get_job_key(job_id))
        except Exception:
            return None

    @staticmethod
    def set_job_state(
        job_id: str,
        status: str,
        academy_id: int,
        event_id: int,
        total: int,
        processed: int = 0,
        results: Optional[list] = None,
        error: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        checkins: Optional[list] = None,
        author_user_id: Optional[int] = None,
        run_marketing: bool = False,
    ) -> None:
        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return
            now = timezone.now().isoformat()
            state = {
                "status": status,
                "academy_id": academy_id,
                "event_id": event_id,
                "run_marketing": run_marketing,
                "total": total,
                "processed": processed,
                "results": results or [],
                "created_at": created_at or now,
                "updated_at": updated_at or now,
                "error": error,
            }
            if checkins is not None:
                state["checkins"] = checkins
            if author_user_id is not None:
                state["author_user_id"] = author_user_id
            cache.set(
                BulkEventCheckinManager.get_job_key(job_id),
                state,
                timeout=BulkEventCheckinManager.TTL_SECONDS,
            )
        except Exception as e:
            logger.warning("set_job_state failed: %s", e)

    @staticmethod
    def update_job_state(job_id: str, **kwargs: Any) -> bool:
        state = BulkEventCheckinManager.get_job_state(job_id)
        if state is None:
            return False
        state["updated_at"] = timezone.now().isoformat()
        for key, value in kwargs.items():
            state[key] = value
        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return False
            cache.set(
                BulkEventCheckinManager.get_job_key(job_id),
                state,
                timeout=BulkEventCheckinManager.TTL_SECONDS,
            )
            return True
        except Exception as e:
            logger.warning("update_job_state failed: %s", e)
            return False


BulkEventCheckinScenario = BulkEventCheckinManager.Scenario
classify_bulk_event_checkin_row = BulkEventCheckinManager.classify_row
validate_bulk_event_checkin_row = BulkEventCheckinManager.validate_row
process_bulk_event_checkin_row = BulkEventCheckinManager.process_row
get_bulk_job_key = BulkEventCheckinManager.get_job_key
get_bulk_job_state = BulkEventCheckinManager.get_job_state
set_bulk_job_state = BulkEventCheckinManager.set_job_state
update_bulk_job_state = BulkEventCheckinManager.update_job_state
