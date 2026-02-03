"""
Bulk student upload: scenario classification and single-row processing.

Used by POST /v1/auth/academy/student/invite/bulk (async task) and POST .../invite/bulk?soft=true (sync validate).
"""
import logging
from enum import Enum
from typing import Any, Optional

from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User

from breathecode.admissions.models import Cohort, CohortUser
from breathecode.authenticate.models import ProfileAcademy, UserInvite

logger = logging.getLogger(__name__)


class BulkStudentManager:
    """Manager for bulk student upload: classify, validate, process rows and Redis job state."""

    class Scenario(str, Enum):
        NEW_USER = "NEW_USER"
        ALREADY_IN_COHORT = "ALREADY_IN_COHORT"
        SAME_ACADEMY_DIFFERENT_COHORT = "SAME_ACADEMY_DIFFERENT_COHORT"
        DIFFERENT_ACADEMY_NO_PROFILE = "DIFFERENT_ACADEMY_NO_PROFILE"
        DIFFERENT_ACADEMY_HAS_PROFILE = "DIFFERENT_ACADEMY_HAS_PROFILE"

    KEY_PREFIX = "bulk_student_upload"
    TTL_SECONDS = 24 * 60 * 60  # 24 hours

    @staticmethod
    def _error_item_message(item: Any) -> str:
        """Extract user-facing message from DRF ErrorDetail or similar (avoids repr with ErrorDetail(string=...))."""
        if hasattr(item, "detail"):
            return str(item.detail)
        if getattr(item, "string", None) is not None:
            return str(item.string)
        return str(item)

    @staticmethod
    def _format_validation_errors(errors: Any) -> str:
        """Convert DRF serializer errors (dict of field -> list of ErrorDetail) to a user-friendly message."""
        try:
            errors = dict(errors) if hasattr(errors, "items") and not isinstance(errors, dict) else errors
        except (TypeError, ValueError):
            pass
        if not isinstance(errors, dict):
            return str(errors)
        parts = []
        for key, value in errors.items():
            if key in ("slug", "detail") and isinstance(value, str):
                continue
            label = key.replace("_", " ").strip().title()
            if isinstance(value, (list, tuple)):
                for item in value:
                    parts.append(f"{label}: {BulkStudentManager._error_item_message(item)}")
            elif isinstance(value, dict) or (hasattr(value, "items") and hasattr(value, "keys")):
                nested = BulkStudentManager._format_validation_errors(value)
                parts.append(f"{label}: {nested}")
            else:
                parts.append(f"{label}: {BulkStudentManager._error_item_message(value)}")
        return " ".join(parts) if parts else str(errors)

    @staticmethod
    def classify_row(academy_id: int, cohort_id: int, email: str) -> "BulkStudentManager.Scenario":
        """
        Classify a row into one of the five bulk-upload scenarios.
        Raises ValidationException if email is blank or if the cohort does not exist or does not belong to the academy.
        """
        email = (email or "").strip().lower()
        if not email:
            raise ValidationException(
                "Email is required",
                slug="email-required",
                code=400,
            )

        cohort = Cohort.objects.filter(id=cohort_id, academy_id=academy_id).first()
        if not cohort:
            raise ValidationException(
                "Cohort not found or does not belong to this academy",
                slug="cohort-not-found",
                code=404,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return BulkStudentManager.Scenario.NEW_USER

        in_cohort = CohortUser.objects.filter(user=user, cohort=cohort).exists()
        if in_cohort:
            return BulkStudentManager.Scenario.ALREADY_IN_COHORT

        has_profile_this_academy = ProfileAcademy.objects.filter(user=user, academy_id=academy_id).exists()
        if has_profile_this_academy:
            other_academies = ProfileAcademy.objects.filter(user=user).exclude(academy_id=academy_id).exists()
            if other_academies:
                return BulkStudentManager.Scenario.DIFFERENT_ACADEMY_HAS_PROFILE
            return BulkStudentManager.Scenario.SAME_ACADEMY_DIFFERENT_COHORT

        return BulkStudentManager.Scenario.DIFFERENT_ACADEMY_NO_PROFILE

    @staticmethod
    def _row_result(
        classification: "BulkStudentManager.Scenario",
        row_data: dict,
        status: str,
        message: Optional[str] = None,
        profile_academy_id: Optional[int] = None,
        cohort_user_id: Optional[int] = None,
        slug: Optional[str] = None,
    ) -> dict:
        """Build a result dict with classification and student fields from row_data."""
        email = (row_data.get("email") or "").strip().lower()
        return {
            "classification": classification.value,
            "email": email,
            "first_name": row_data.get("first_name"),
            "last_name": row_data.get("last_name"),
            "phone": row_data.get("phone"),
            "status": status,
            "message": message,
            "profile_academy_id": profile_academy_id,
            "cohort_user_id": cohort_user_id,
            "slug": slug,
        }

    @staticmethod
    def validate_row(
        academy_id: int,
        cohort_id: int,
        row_data: dict,
        payment_method: Optional[int] = None,
        plans: Optional[list[int]] = None,
    ) -> dict:
        """
        Validate and classify a row without creating any records (used when ?soft=true).
        Returns result with classification and status (created/skipped/failed).
        """
        email = (row_data.get("email") or "").strip().lower()
        if not email:
            return BulkStudentManager._row_result(
                BulkStudentManager.Scenario.NEW_USER,
                row_data,
                "failed",
                message="Email is required",
                slug="email-required",
            )

        try:
            classification = BulkStudentManager.classify_row(academy_id, cohort_id, email)
        except ValidationException as e:
            slug = getattr(e, "slug", None) or "cohort-not-found"
            return BulkStudentManager._row_result(
                BulkStudentManager.Scenario.NEW_USER,
                row_data,
                "failed",
                message=str(getattr(e, "detail", e)),
                slug=slug,
            )

        if classification == BulkStudentManager.Scenario.ALREADY_IN_COHORT:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "skipped",
                message="User is already in this cohort",
            )

        if plans and classification != BulkStudentManager.Scenario.NEW_USER:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message="Cannot add payment plans when user already exists.",
                slug="cannot-add-plans-to-existing-user",
            )

        cohort = Cohort.objects.filter(id=cohort_id, academy_id=academy_id).first()
        if not cohort:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message="Cohort not found or does not belong to this academy",
                slug="cohort-not-found",
            )

        if cohort.stage in ("INACTIVE", "DELETED", "ENDED"):
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message=f"Cohort is {cohort.stage}",
                slug="cohort-not-available",
            )

        if classification == BulkStudentManager.Scenario.NEW_USER:
            existing = ProfileAcademy.objects.filter(email__iexact=email, academy_id=academy_id).first()
            if existing:
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "failed",
                    message="There is a student already in this academy, or with invitation pending",
                    slug="already-exists-with-this-email",
                )
            invite = UserInvite.objects.filter(email__iexact=email, academy_id=academy_id).first()
            if invite:
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "failed",
                    message="You already invited this user",
                    slug="already-invited",
                )

        return BulkStudentManager._row_result(classification, row_data, "created")

    @staticmethod
    def process_row(
        academy_id: int,
        cohort_id: int,
        row_data: dict,
        author_user_id: int,
        invite: bool = True,
        payment_method: Optional[int] = None,
        plans: Optional[list[int]] = None,
    ) -> dict:
        """
        Classify and process one row: create/skip/fail. Returns result with classification,
        student fields, status, and optional profile_academy_id/cohort_user_id.
        """
        from breathecode.authenticate.serializers import StudentPOSTSerializer

        email = (row_data.get("email") or "").strip().lower()
        if not email:
            return BulkStudentManager._row_result(
                BulkStudentManager.Scenario.NEW_USER,
                row_data,
                "failed",
                message="Email is required",
                slug="email-required",
            )

        try:
            classification = BulkStudentManager.classify_row(academy_id, cohort_id, email)
        except ValidationException as e:
            slug = getattr(e, "slug", None) or "cohort-not-found"
            return BulkStudentManager._row_result(
                BulkStudentManager.Scenario.NEW_USER,
                row_data,
                "failed",
                message=str(getattr(e, "detail", e)),
                slug=slug,
            )

        if classification == BulkStudentManager.Scenario.ALREADY_IN_COHORT:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "skipped",
                message="User is already in this cohort",
            )

        author = User.objects.filter(id=author_user_id).first()
        if not author:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message="Author user not found",
                slug="author-not-found",
            )

        cohort = Cohort.objects.filter(id=cohort_id, academy_id=academy_id).first()
        if not cohort:
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message="Cohort not found or does not belong to this academy",
                slug="cohort-not-found",
            )

        if cohort.stage in ("INACTIVE", "DELETED", "ENDED"):
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "failed",
                message=f"Cannot add to cohort that is {cohort.stage}",
                slug="adding-student-to-a-closed-cohort",
            )

        if classification in (
            BulkStudentManager.Scenario.SAME_ACADEMY_DIFFERENT_COHORT,
            BulkStudentManager.Scenario.DIFFERENT_ACADEMY_HAS_PROFILE,
        ):
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "failed",
                    message="User not found",
                    slug="user-not-found",
                )
            cohort_user, _ = CohortUser.objects.get_or_create(
                cohort=cohort,
                user=user,
                role="STUDENT",
                defaults={
                    "finantial_status": "UP_TO_DATE",
                    "educational_status": "ACTIVE",
                },
            )
            return BulkStudentManager._row_result(
                classification,
                row_data,
                "created",
                profile_academy_id=None,
                cohort_user_id=cohort_user.id,
            )

        if classification in (BulkStudentManager.Scenario.NEW_USER, BulkStudentManager.Scenario.DIFFERENT_ACADEMY_NO_PROFILE):
            data = {
                "email": email,
                "first_name": row_data.get("first_name") or "",
                "last_name": row_data.get("last_name") or "",
                "phone": row_data.get("phone") or "",
                "cohort": [cohort_id],
                "invite": invite,
            }
            user = User.objects.filter(email__iexact=email).first()
            if user:
                data["user"] = user.id
                if plans:
                    data.pop("plans", None)
            else:
                if payment_method is not None:
                    data["payment_method"] = payment_method
                if plans:
                    data["plans"] = plans

            class MockRequest:
                user = author

            serializer = StudentPOSTSerializer(
                data=data,
                context={"academy_id": academy_id, "request": MockRequest()},
            )
            try:
                if not serializer.is_valid():
                    errors = serializer.errors
                    msg = BulkStudentManager._format_validation_errors(errors)
                    slug = None
                    if isinstance(errors, dict):
                        for key in ("slug", "detail"):
                            if key in errors and isinstance(errors[key], str):
                                slug = errors[key]
                                break
                    return BulkStudentManager._row_result(
                        classification,
                        row_data,
                        "failed",
                        message=msg,
                        slug=slug or "validation-error",
                    )
                profile_academy = serializer.save()
                cohort_user = CohortUser.objects.filter(user=profile_academy.user, cohort=cohort).first()
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "created",
                    profile_academy_id=profile_academy.id,
                    cohort_user_id=cohort_user.id if cohort_user else None,
                )
            except ValidationException as e:
                detail = getattr(e, "detail", None)
                if detail is not None and isinstance(detail, dict):
                    msg = BulkStudentManager._format_validation_errors(detail)
                else:
                    msg = str(detail) if detail is not None else str(e)
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "failed",
                    message=msg,
                    slug=getattr(e, "slug", None) or "validation-error",
                )
            except Exception as e:
                logger.exception("process_row failed for email=%s", email)
                return BulkStudentManager._row_result(
                    classification,
                    row_data,
                    "failed",
                    message=str(e),
                    slug="unexpected-error",
                )

        return BulkStudentManager._row_result(
            classification, row_data, "failed", message="Unknown classification", slug="unknown"
        )

    @staticmethod
    def get_job_key(job_id: str) -> str:
        return f"{BulkStudentManager.KEY_PREFIX}:{job_id}"

    @staticmethod
    def get_job_state(job_id: str) -> Optional[dict]:
        """Load job state from Redis. Returns None if key missing or Redis unavailable."""
        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return None
            key = BulkStudentManager.get_job_key(job_id)
            return cache.get(key)
        except Exception:
            return None

    @staticmethod
    def set_job_state(
        job_id: str,
        status: str,
        academy_id: int,
        total: int,
        processed: int = 0,
        results: Optional[list] = None,
        error: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        students: Optional[list] = None,
        author_user_id: Optional[int] = None,
    ) -> None:
        """Write job state to Redis with TTL. students and author_user_id stored for task (each student has own cohort_id)."""
        from django.utils import timezone

        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return
            now = timezone.now().isoformat()
            key = BulkStudentManager.get_job_key(job_id)
            state = {
                "status": status,
                "academy_id": academy_id,
                "total": total,
                "processed": processed,
                "results": results or [],
                "created_at": created_at or now,
                "updated_at": updated_at or now,
                "error": error,
            }
            if students is not None:
                state["students"] = students
            if author_user_id is not None:
                state["author_user_id"] = author_user_id
            cache.set(key, state, timeout=BulkStudentManager.TTL_SECONDS)
        except Exception as e:
            logger.warning("set_job_state failed: %s", e)

    @staticmethod
    def update_job_state(job_id: str, **kwargs: Any) -> bool:
        """Update job state in Redis. Merges kwargs into existing state. Returns True if updated."""
        state = BulkStudentManager.get_job_state(job_id)
        if state is None:
            return False
        from django.utils import timezone

        state["updated_at"] = timezone.now().isoformat()
        for key, value in kwargs.items():
            state[key] = value
        try:
            from django.core.cache import cache

            if hasattr(cache, "fake"):
                return False
            key = BulkStudentManager.get_job_key(job_id)
            cache.set(key, state, timeout=BulkStudentManager.TTL_SECONDS)
            return True
        except Exception as e:
            logger.warning("update_job_state failed: %s", e)
            return False


# Public API: same names as before for drop-in import change
BulkStudentScenario = BulkStudentManager.Scenario
classify_bulk_student_row = BulkStudentManager.classify_row
validate_bulk_student_row = BulkStudentManager.validate_row
process_bulk_student_row = BulkStudentManager.process_row
get_bulk_job_key = BulkStudentManager.get_job_key
get_bulk_job_state = BulkStudentManager.get_job_state
set_bulk_job_state = BulkStudentManager.set_job_state
update_bulk_job_state = BulkStudentManager.update_job_state
