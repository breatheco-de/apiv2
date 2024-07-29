import logging
import os
from typing import Any

import requests
from celery import shared_task
from task_manager.core.exceptions import AbortTask
from task_manager.django.decorators import task

import breathecode.activity.tasks as tasks_activity
from breathecode.services.calendly import Calendly
from breathecode.services.calendly.actions import invitee_created
from breathecode.utils.decorators import TaskPriority

from .models import CalendlyOrganization, CalendlyWebhook, MentorProfile

logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def async_calendly_webhook(self, calendly_webhook_id):
    logger.debug("Starting async_calendly_webhook")
    status = "ok"

    webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()
    organization = webhook.organization
    if organization is None:
        organization = CalendlyOrganization.objects.filter(hash=webhook.organization_hash).first()

    if organization:
        try:
            client = Calendly(organization.access_token)
            client.execute_action(calendly_webhook_id)
        except Exception as e:
            logger.debug("Calendly webhook exception")
            logger.debug(str(e))
            status = "error"

    else:
        message = f"Calendly Organization {organization.id} doesn't exist"

        webhook.status = "ERROR"
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = "error"

    logger.debug(f"Calendly status: {status}")


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def async_mentorship_session_calendly_webhook(self, calendly_webhook_id):
    logger.debug("Starting async_mentorship_session_calendly_webhook")

    webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()

    payload = webhook.payload
    calendly_token = os.getenv("CALENDLY_TOKEN")
    client = Calendly(calendly_token)
    payload["tracking"]["utm_campaign"] = "geekpal"
    mentorship_session = invitee_created(client, webhook, payload)

    if mentorship_session is not None:
        tasks_activity.add_activity.delay(
            mentorship_session.mentee.id,
            "mentoring_session_scheduled",
            related_type="mentorship.MentorshipSession",
            related_id=mentorship_session.id,
            timestamp=webhook.called_at,
        )


@task(bind=False, priority=TaskPriority.STUDENT.value)
def check_mentorship_profile(mentor_id: int, **_: Any):
    mentor = MentorProfile.objects.filter(id=mentor_id).first()
    if mentor is None:
        raise AbortTask(f"Mentorship profile {mentor_id} not found")

    status = []

    if mentor.online_meeting_url is None or mentor.online_meeting_url == "":
        status.append("no-online-meeting-url")

    if mentor.booking_url is None or "https://calendly.com" not in mentor.booking_url:
        status.append("no-booking-url")

    if len(mentor.syllabus.all()) == 0:
        status.append("no-syllabus")

    if "no-online-meeting-url" not in status:
        response = requests.head(mentor.online_meeting_url, timeout=30)
        if response.status_code > 399:
            status.append("bad-online-meeting-url")

    if "no-booking-url" not in status:
        response = requests.head(mentor.booking_url, timeout=30)
        if response.status_code > 399:
            status.append("bad-booking-url")

    mentor.availability_report = status
    mentor.save()
