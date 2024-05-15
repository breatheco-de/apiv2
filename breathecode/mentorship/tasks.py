import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import pytz
import requests
from celery import shared_task
from google.apps.meet_v2.types import Space, SpaceConfig
from task_manager.core.exceptions import AbortTask
from task_manager.django.decorators import task

import breathecode.activity.tasks as tasks_activity
import breathecode.notify.actions as notify_actions
from breathecode.authenticate.actions import get_user_settings
from breathecode.services.calendly import Calendly
from breathecode.services.calendly.actions import invitee_created
from breathecode.services.google_meet.google_meet import GoogleMeet
from breathecode.utils.decorators import TaskPriority
from breathecode.utils.i18n import translation

from .models import CalendlyOrganization, CalendlyWebhook, MentorProfile, MentorshipSession

logger = logging.getLogger(__name__)


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def async_calendly_webhook(self, calendly_webhook_id):
    logger.debug('Starting async_calendly_webhook')
    status = 'ok'

    webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()
    organization = webhook.organization
    if organization is None:
        organization = CalendlyOrganization.objects.filter(hash=webhook.organization_hash).first()

    if organization:
        try:
            client = Calendly(organization.access_token)
            client.execute_action(calendly_webhook_id)
        except Exception as e:
            logger.debug('Calendly webhook exception')
            logger.debug(str(e))
            status = 'error'

    else:
        message = f"Calendly Organization {organization.id} doesn\'t exist"

        webhook.status = 'ERROR'
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        status = 'error'

    logger.debug(f'Calendly status: {status}')


@shared_task(bind=True, priority=TaskPriority.STUDENT.value)
def async_mentorship_session_calendly_webhook(self, calendly_webhook_id):
    logger.debug('Starting async_mentorship_session_calendly_webhook')

    webhook = CalendlyWebhook.objects.filter(id=calendly_webhook_id).first()

    payload = webhook.payload
    calendly_token = os.getenv('CALENDLY_TOKEN')
    client = Calendly(calendly_token)
    payload['tracking']['utm_campaign'] = 'geekpal'
    mentorship_session = invitee_created(client, webhook, payload)

    if mentorship_session is not None:
        tasks_activity.add_activity.delay(
            mentorship_session.mentee.id,
            'mentoring_session_scheduled',
            related_type='mentorship.MentorshipSession',
            related_id=mentorship_session.id,
            timestamp=webhook.called_at,
        )


@task(bind=False, priority=TaskPriority.STUDENT.value)
def check_mentorship_profile(mentor_id: int, **_: Any):
    mentor = MentorProfile.objects.filter(id=mentor_id).first()
    if mentor is None:
        raise AbortTask(f'Mentorship profile {mentor_id} not found')

    status = []

    if mentor.online_meeting_url is None or mentor.online_meeting_url == '':
        status.append('no-online-meeting-url')

    if mentor.booking_url is None or 'https://calendly.com' not in mentor.booking_url:
        status.append('no-booking-url')

    if len(mentor.syllabus.all()) == 0:
        status.append('no-syllabus')

    if 'no-online-meeting-url' not in status:
        response = requests.head(mentor.online_meeting_url, timeout=30)
        if response.status_code > 399:
            status.append('bad-online-meeting-url')

    if 'no-booking-url' not in status:
        response = requests.head(mentor.booking_url, timeout=30)
        if response.status_code > 399:
            status.append('bad-booking-url')

    mentor.availability_report = status
    mentor.save()


def localize_date(dt: datetime, timezone: str = 'UTC'):
    # Localize the datetime object to the specified timezone
    local_tz = pytz.timezone(timezone)
    localized_dt = dt.astimezone(local_tz)

    # Format the localized datetime object to a string
    localized_string = localized_dt.strftime('%Y-%m-%d %I:%M:%S %p')

    return localized_string


@task(bind=False, priority=TaskPriority.STUDENT.value)
def cancellate_conference_on_google_meet(session_id: int, **_: Any):
    """Cancellate conference on google meet for a mentorship session."""

    def get_translations(lang: str) -> dict[str, str]:
        return {
            'organizers': translation(lang, en='Organizers', es='Organizadores'),
            'invitees': translation(lang, en='Invitees', es='Invitados'),
            'date': translation(lang, en='Date', es='Fecha'),
            'duration': translation(lang, en='Duration', es='Duración'),
            'location': translation(lang, en='Location', es='Ubicación'),
            'enter': translation(lang, en='Enter', es='Entrar'),
            'cancel': translation(lang, en='Cancel', es='Cancelar'),
            'details': translation(lang, en='Details', es='Detalles'),
            'qaa': translation(lang, en='Questions and Answers', es='Preguntas y Respuestas'),
        }

    session = MentorshipSession.objects.filter(id=session_id, service__video_provider='GOOGLE_MEET').first()

    if session is None:
        raise AbortTask(f'Mentorship session {session_id} not found')

    if session.mentee is None:
        raise AbortTask(f'This session doesn\'t have a mentee')

    if not session.service:
        raise AbortTask(f'Mentorship session doesn\'t have a service associated with it')

    mentor = session.mentor
    mentee = session.mentee

    meet = GoogleMeet()
    title = (f'{session.service.name} {session.id} | '
             f'{mentor.user.first_name} {mentor.user.last_name} | '
             f'{mentee.first_name} {mentee.last_name}')

    meet.end_active_conference(name=title)


@task(bind=False, priority=TaskPriority.STUDENT.value)
def create_room_on_google_meet(session_id: int, **_: Any):
    """Create a room on google meet for a mentorship session."""

    def get_translations(lang: str) -> dict[str, str]:
        return {
            'organizers': translation(lang, en='Organizers', es='Organizadores'),
            'invitees': translation(lang, en='Invitees', es='Invitados'),
            'date': translation(lang, en='Date', es='Fecha'),
            'duration': translation(lang, en='Duration', es='Duración'),
            'location': translation(lang, en='Location', es='Ubicación'),
            'enter': translation(lang, en='Enter', es='Entrar'),
            'cancel': translation(lang, en='Cancel', es='Cancelar'),
            'details': translation(lang, en='Details', es='Detalles'),
            'qaa': translation(lang, en='Questions and Answers', es='Preguntas y Respuestas'),
        }

    session = MentorshipSession.objects.filter(id=session_id, service__video_provider='GOOGLE_MEET').first()

    if session is None:
        raise AbortTask(f'Mentorship session {session_id} not found')

    if session.mentee is None:
        raise AbortTask(f'This session doesn\'t have a mentee')

    if not session.service:
        raise AbortTask(f'Mentorship session doesn\'t have a service associated with it')

    if session.starts_at is None:
        raise AbortTask(f'Mentorship session {session_id} doesn\'t have a start date')

    if session.ends_at is None:
        raise AbortTask(f'Mentorship session {session_id} doesn\'t have an end date')

    mentor = session.mentor
    mentee = session.mentee

    meet = GoogleMeet()
    title = (f'{session.service.name} {session.id} | '
             f'{mentor.user.first_name} {mentor.user.last_name} | '
             f'{mentee.first_name} {mentee.last_name}')
    s = Space(
        name=title,
        config=SpaceConfig(access_type=SpaceConfig.AccessType.OPEN),
    )
    space = meet.create_space(space=s)

    mentor_lang = get_user_settings(mentor.user.id).lang
    mentee_lang = get_user_settings(mentee.id).lang

    answers = session.questions_and_answers or []
    api_url = os.getenv('API_URL', '')
    if api_url.endswith('/'):
        api_url = api_url[:-1]

    academy = None
    if session.mentor.academy and session.mentor.academy.timezone:
        academy = session.mentor.academy

    if academy is None and session.service.academy and session.service.academy.timezone:
        academy = session.service.academy

    timezone = academy.timezone if academy is not None else 'UTC'

    try:
        local_tz = pytz.timezone(timezone)

    except pytz.exceptions.UnknownTimeZoneError:
        local_tz = pytz.timezone('UTC')

    localized_dt = session.starts_at.astimezone(local_tz)

    # Format the localized datetime object to a string
    localized_string = localized_dt.strftime('%Y-%m-%d %I:%M:%S %p')

    data = {
        'title': session.service.name,
        'description': session.service.description,
        'meet': {
            'url': space.meeting_uri,
            'cancellation_url': api_url + f'/mentor/session/{session.id}/cancel',
            'date': session.starts_at.isoformat(),
            'preformatted_date': localized_string,
            'duration': session.ends_at - session.starts_at,
        },
        'organizers': [
            {
                'name': f'{mentor.user.first_name} {mentor.user.last_name}',
            },
        ],
        'invitees': [
            {
                'name': f'{mentee.first_name} {mentee.last_name}',
                'email': mentee.email,
            },
        ],
        'answers': answers,
    }

    if mentor_lang == mentee_lang:
        emails = [mentor.user.email, mentee.email]

        data['translations'] = get_translations(mentor_lang)
        notify_actions.send_email_message('meet_notification', emails, data)

    else:
        emails = [mentor.user.email]
        notify_actions.send_email_message('meet_notification', emails, {
            **data,
            'translations': get_translations(mentor_lang),
        })

        emails = [mentee.email]
        notify_actions.send_email_message('meet_notification', emails, {
            **data,
            'translations': get_translations(mentee_lang),
        })
