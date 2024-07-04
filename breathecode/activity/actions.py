import functools
import os
from datetime import datetime
from typing import Any, Optional, TypedDict

from django.core.cache import cache
from task_manager.core.exceptions import AbortTask, RetryTask

ALLOWED_TYPES = {
    "auth.UserInvite": [
        "invite_created",
        "invite_status_updated",
    ],
    "feedback.Answer": [
        "nps_answered",
    ],
    "auth.User": [
        "login",
    ],
    "admissions.CohortUser": [
        "joined_cohort",
    ],
    "assignments.Task": [
        "open_syllabus_module",
        "read_assignment",
        "assignment_review_status_updated",
        "assignment_status_updated",
    ],
    "events.EventCheckin": [
        "event_checkin_created",
        "event_checkin_assisted",
    ],
    "payments.Bag": [
        "bag_created",
    ],
    "payments.Subscription": [
        "checkout_completed",
    ],
    "payments.PlanFinancing": [
        "checkout_completed",
    ],
    "mentorship.MentorshipSession": [
        "mentoring_session_scheduled",
        "mentorship_session_checkin",
        "mentorship_session_checkout",
    ],
    "payments.Invoice": [
        "checkout_completed",
    ],
}


class FillActivityMeta:

    @staticmethod
    def _get_query(related_id: Optional[str | int] = None, related_slug: Optional[str] = None) -> dict[str, Any]:
        kwargs = {}

        if related_id:
            kwargs["pk"] = related_id

        if related_slug:
            kwargs["slug"] = related_slug

        return kwargs

    @classmethod
    def user_invite(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.authenticate.models import UserInvite

        kwargs = cls._get_query(related_id, related_slug)
        instance = UserInvite.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"UserInvite {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "email": instance.email,
            "phone": instance.phone,
            "status": instance.status,
            "process_status": instance.process_status,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
        }

        if instance.author:
            obj["author_email"] = instance.author.email
            obj["author_username"] = instance.author.username

        if instance.user:
            obj["user_email"] = instance.user.email
            obj["user_username"] = instance.user.username
            obj["user_first_name"] = instance.user.first_name
            obj["user_last_name"] = instance.user.last_name

        if instance.role:
            obj["role"] = instance.role.slug

        if instance.academy:
            obj["academy"] = instance.academy.id

        if instance.cohort:
            obj["cohort"] = instance.cohort.id

        return obj

    @classmethod
    def answer(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.feedback.models import Answer

        kwargs = cls._get_query(related_id, related_slug)
        instance = Answer.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Answer {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "title": instance.title,
            "lowest": instance.lowest,
            "highest": instance.highest,
            "lang": instance.lang,
            "score": instance.score,
            "comment": instance.comment,
            "status": instance.status,
        }

        if instance.user:
            obj["user_email"] = instance.user.email
            obj["user_username"] = instance.user.username
            obj["user_first_name"] = instance.user.first_name
            obj["user_last_name"] = instance.user.last_name

        if instance.mentor:
            obj["mentor_email"] = instance.mentor.email
            obj["mentor_username"] = instance.mentor.username
            obj["mentor_first_name"] = instance.mentor.first_name
            obj["mentor_last_name"] = instance.mentor.last_name

        if instance.academy:
            obj["academy"] = instance.academy.id

        if instance.cohort:
            obj["cohort"] = instance.cohort.id

        if instance.survey:
            obj["survey"] = instance.survey.id

        if instance.mentorship_session:
            obj["mentorship_session"] = instance.mentorship_session.name

        if instance.event:
            obj["event"] = instance.event.slug

        if instance.opened_at:
            obj["opened_at"] = instance.opened_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.sent_at:
            obj["sent_at"] = instance.sent_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def user(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.authenticate.models import User

        kwargs = cls._get_query(related_id, related_slug)
        instance = User.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"User {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "email": instance.email,
            "username": instance.username,
        }

        return obj

    @classmethod
    def cohort(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.admissions.models import Cohort

        kwargs = cls._get_query(related_id, related_slug)
        instance = Cohort.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Cohort {related_id or related_slug} not found")

        syllabus = (
            f"{instance.syllabus_version.syllabus.slug}.v{instance.syllabus_version.version}"
            if instance.syllabus_version
            else None
        )
        obj = {
            "id": instance.id,
            "slug": instance.slug,
            "name": instance.name,
            "current_day": instance.current_day,
            "current_module": instance.current_module,
            "stage": instance.stage,
            "private": instance.private,
            "accepts_enrollment_suggestions": instance.accepts_enrollment_suggestions,
            "never_ends": instance.never_ends,
            "remote_available": instance.remote_available,
            "online_meeting_url": instance.online_meeting_url,
            "timezone": instance.timezone,
            "syllabus": syllabus,
            "intro_video": instance.intro_video,
            "is_hidden_on_prework": instance.is_hidden_on_prework,
            "available_as_saas": instance.available_as_saas,
            "language": instance.language,
        }

        if instance.academy:
            obj["academy"] = instance.academy.id

        if instance.schedule:
            obj["schedule"] = instance.schedule.name

        if instance.kickoff_date:
            obj["kickoff_date"] = instance.kickoff_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.ending_date:
            obj["ending_date"] = instance.ending_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def cohort_user(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.admissions.models import CohortUser

        kwargs = cls._get_query(related_id, related_slug)
        instance = CohortUser.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"CohortUser {related_id or related_slug} not found")

        # syllabus = (
        #     f'{instance.cohort.syllabus_version.syllabus.slug}.v{instance.cohort.syllabus_version.version}'
        #     if instance.cohort.syllabus_version else None)
        obj = {
            "id": instance.id,
            "user_first_name": instance.user.first_name,
            "user_last_name": instance.user.last_name,
            "cohort": instance.cohort.id,
            # 'available_as_saas': instance.cohort.available_as_saas,
            # 'syllabus': syllabus,
            # 'user_id': instance.user.id,
            # 'watching': instance.watching,
            # 'finantial_status': instance.finantial_status,
            # 'educational_status': instance.educational_status,
            # 'created_at': instance.created_at,
            # 'updated_at': instance.updated_at,
        }

        if instance.cohort.academy:
            obj["academy"] = instance.cohort.academy.id

        return obj

    @classmethod
    def task(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.assignments.models import Task

        kwargs = cls._get_query(related_id, related_slug)
        instance = Task.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Task {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "associated_slug": instance.associated_slug,
            "title": instance.title,
            "task_status": instance.task_status,
            "revision_status": instance.revision_status,
            "task_type": instance.task_type,
            "github_url": instance.github_url,
            "live_url": instance.live_url,
        }

        if instance.user:
            obj["user_email"] = instance.user.email
            obj["user_username"] = instance.user.username
            obj["user_first_name"] = instance.user.first_name
            obj["user_last_name"] = instance.user.last_name

        if instance.cohort:
            obj["cohort"] = instance.cohort.id
            obj["academy"] = instance.cohort.academy.id

        if instance.opened_at:
            obj["opened_at"] = instance.opened_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def event_checkin(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.events.models import EventCheckin

        kwargs = cls._get_query(related_id, related_slug)
        instance = EventCheckin.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"EventCheckin {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "email": instance.email,
            "event_id": instance.event.id,
            "event_slug": instance.event.slug,
            "status": instance.status,
        }

        if instance.attendee:
            obj["attendee_email"] = instance.attendee.email
            obj["attendee_username"] = instance.attendee.username
            obj["attendee_first_name"] = instance.attendee.first_name
            obj["attendee_last_name"] = instance.attendee.last_name

        if instance.attended_at:
            obj["attended_at"] = instance.attended_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def mentorship_session(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.mentorship.models import MentorshipSession

        kwargs = cls._get_query(related_id, related_slug)
        instance = MentorshipSession.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"MentorshipSession {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "name": instance.name,
            "is_online": instance.is_online,
            "latitude": instance.latitude,
            "longitude": instance.longitude,
            "online_meeting_url": instance.online_meeting_url,
            "online_recording_url": instance.online_recording_url,
            "status": instance.status,
            "allow_billing": instance.allow_billing,
            "suggested_accounted_duration": instance.suggested_accounted_duration,
            "accounted_duration": instance.accounted_duration,
        }

        if instance.mentor:
            obj["mentor_id"] = instance.mentor.id
            obj["mentor_slug"] = instance.mentor.slug
            obj["mentor_name"] = instance.mentor.name

        if instance.mentee:
            obj["mentee_email"] = instance.mentee.email
            obj["mentee_username"] = instance.mentee.username
            obj["mentee_first_name"] = instance.mentee.first_name
            obj["mentee_last_name"] = instance.mentee.last_name

        if instance.service:
            obj["service"] = instance.service.slug
            obj["academy"] = instance.service.academy.id

        if instance.bill:
            obj["bill"] = instance.bill.id

        if instance.starts_at:
            obj["starts_at"] = instance.starts_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.ends_at:
            obj["ends_at"] = instance.ends_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.started_at:
            obj["started_at"] = instance.started_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.ended_at:
            obj["ended_at"] = instance.ended_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.mentor_joined_at:
            obj["mentor_joined_at"] = instance.mentor_joined_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.mentor_left_at:
            obj["mentor_left_at"] = instance.mentor_left_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.mentee_left_at:
            obj["mentee_left_at"] = instance.mentee_left_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def invoice(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.payments.models import Invoice

        kwargs = cls._get_query(related_id, related_slug)
        instance = Invoice.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Invoice {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "amount": instance.amount,
            "currency": instance.currency.code,
            "status": instance.status,
            "bag": instance.bag.id,
            "academy": instance.academy.id,
            "user_email": instance.user.email,
            "user_username": instance.user.username,
            "user_first_name": instance.user.first_name,
            "user_last_name": instance.user.last_name,
        }

        if instance.paid_at:
            obj["paid_at"] = instance.paid_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.refunded_at:
            obj["refunded_at"] = instance.refunded_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def bag(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.payments.models import Bag

        kwargs = cls._get_query(related_id, related_slug)
        instance = Bag.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Bag {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "status": instance.status,
            "type": instance.type,
            "chosen_period": instance.chosen_period,
            "how_many_installments": instance.how_many_installments,
            "academy": instance.academy.id,
            "user_email": instance.user.email,
            "user_username": instance.user.username,
            "user_first_name": instance.user.first_name,
            "user_last_name": instance.user.last_name,
            "is_recurrent": instance.is_recurrent,
            "was_delivered": instance.was_delivered,
        }

        if instance.expires_at:
            obj["expires_at"] = instance.expires_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def subscription(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.payments.models import Subscription

        kwargs = cls._get_query(related_id, related_slug)
        instance = Subscription.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"Subscription {related_id or related_slug} not found")

        obj = {
            "id": instance.id,
            "status": instance.status,
            "user_email": instance.user.email,
            "user_username": instance.user.username,
            "user_first_name": instance.user.first_name,
            "user_last_name": instance.user.last_name,
            "academy": instance.academy.id,
            "is_refundable": instance.is_refundable,
            "pay_every": instance.pay_every,
            "pay_every_unit": instance.pay_every_unit,
        }

        if instance.selected_cohort_set:
            obj["selected_cohort_set"] = instance.selected_cohort_set.slug

        if instance.selected_mentorship_service_set:
            obj["selected_mentorship_service_set"] = instance.selected_mentorship_service_set.slug

        if instance.selected_event_type_set:
            obj["selected_event_type_set"] = instance.selected_event_type_set.slug

        if instance.paid_at:
            obj["paid_at"] = instance.paid_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.next_payment_at:
            obj["next_payment_at"] = instance.next_payment_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.valid_until:
            obj["valid_until"] = instance.valid_until.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj

    @classmethod
    def plan_financing(
        cls, kind: str, related_id: Optional[str | int] = None, related_slug: Optional[str] = None
    ) -> dict[str, Any]:
        from breathecode.payments.models import PlanFinancing

        kwargs = cls._get_query(related_id, related_slug)
        instance = PlanFinancing.objects.filter(**kwargs).first()

        if not instance:
            raise RetryTask(f"PlanFinancing {related_id or related_slug} not found")

        selected_mentorship_service_set = (
            instance.selected_mentorship_service_set.slug if instance.selected_mentorship_service_set else None
        )

        selected_event_type_set = instance.selected_event_type_set.slug if instance.selected_event_type_set else None
        obj = {
            "id": instance.id,
            "status": instance.status,
            "user_email": instance.user.email,
            "user_username": instance.user.username,
            "user_first_name": instance.user.first_name,
            "user_last_name": instance.user.last_name,
            "academy": instance.academy.id,
            "selected_mentorship_service_set": selected_mentorship_service_set,
            "selected_event_type_set": selected_event_type_set,
            "monthly_price": instance.monthly_price,
        }

        if instance.selected_cohort_set:
            obj["selected_cohort_set"] = instance.selected_cohort_set.slug

        if instance.next_payment_at:
            obj["next_payment_at"] = instance.next_payment_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.valid_until:
            obj["valid_until"] = instance.valid_until.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if instance.plan_expires_at:
            obj["plan_expires_at"] = instance.plan_expires_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return obj


def get_activity_meta(
    kind: str,
    related_type: Optional[str] = None,
    related_id: Optional[str | int] = None,
    related_slug: Optional[str] = None,
) -> dict[str, Any]:

    if not related_type:
        return {}

    if related_type and not related_id and not related_slug:
        raise AbortTask("related_id or related_slug must be present")

    if related_type not in ALLOWED_TYPES:
        raise AbortTask(f"{related_type} is not supported yet")

    args = (kind, related_id, related_slug)

    if related_type == "auth.UserInvite" and kind in ALLOWED_TYPES["auth.UserInvite"]:
        return FillActivityMeta.user_invite(*args)

    if related_type == "feedback.Answer" and kind in ALLOWED_TYPES["feedback.Answer"]:
        return FillActivityMeta.answer(*args)

    if related_type == "auth.User" and kind in ALLOWED_TYPES["auth.User"]:
        return FillActivityMeta.user(*args)

    if related_type == "admissions.Cohort" and kind in ALLOWED_TYPES["admissions.Cohort"]:
        return FillActivityMeta.cohort(*args)

    if related_type == "admissions.CohortUser" and kind in ALLOWED_TYPES["admissions.CohortUser"]:
        return FillActivityMeta.cohort_user(*args)

    if related_type == "assignments.Task" and kind in ALLOWED_TYPES["assignments.Task"]:
        return FillActivityMeta.task(*args)

    if related_type == "events.EventCheckin" and kind in ALLOWED_TYPES["events.EventCheckin"]:
        return FillActivityMeta.event_checkin(*args)

    if related_type == "payments.Bag" and kind in ALLOWED_TYPES["payments.Bag"]:
        return FillActivityMeta.bag(*args)

    if related_type == "payments.Subscription" and kind in ALLOWED_TYPES["payments.Subscription"]:
        return FillActivityMeta.subscription(*args)

    if related_type == "payments.PlanFinancing" and kind in ALLOWED_TYPES["payments.PlanFinancing"]:
        return FillActivityMeta.plan_financing(*args)

    if related_type == "mentorship.MentorshipSession" and kind in ALLOWED_TYPES["mentorship.MentorshipSession"]:
        return FillActivityMeta.mentorship_session(*args)

    if related_type == "payments.Invoice" and kind in ALLOWED_TYPES["payments.Invoice"]:
        return FillActivityMeta.invoice(*args)

    raise AbortTask(f"kind {kind} is not supported by {related_type} yet")


@functools.lru_cache(maxsize=1)
def get_workers_amount():
    dynos = int(os.getenv("CELERY_DYNOS") or 1)
    workers = int(os.getenv("CELERY_MAX_WORKERS") or 1)
    return dynos * workers


class Worker(TypedDict):
    pid: int
    created_at: datetime


Workers = dict[int, list[Worker]]


def get_current_worker_number() -> int:
    """
    Return the current worker number for the calling process.

    Assumes the worker data is stored in the cache.
    """

    if os.getenv("CELERY_POOL", "") == "gevent":
        from gevent import getcurrent

        worker_pid = id(getcurrent())
    else:
        worker_pid = os.getpid()

    # Retrieve worker data from the cache
    workers_data: Workers = cache.get("workers", {})

    if not workers_data:
        return 0

    # Find the worker number for the current process
    for worker_number, worker_processes in workers_data.items():
        for worker_process in worker_processes:
            if worker_process["pid"] == worker_pid:
                return worker_number

    # If the process is not found, return None or raise an exception based on your requirements
    return 0
