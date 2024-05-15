"""
This file just can contains duck tests refert to AcademyInviteView
"""
from datetime import datetime, timedelta
from logging import Logger
from unittest.mock import MagicMock, call

import pytest
import pytz
from django.utils import timezone
from google.apps.meet_v2.types import Space, SpaceConfig

import capyc.rest_framework.pytest as capy
from breathecode.mentorship.tasks import cancellate_conference_on_google_meet
from breathecode.notify import actions
from breathecode.services.google_meet.google_meet import GoogleMeet

UTC_NOW = timezone.now()


def localize_datetime(academy, dt: datetime):
    timezone = academy.timezone if academy is not None else 'UTC'

    local_tz = pytz.timezone(timezone)
    localized_dt = dt.astimezone(local_tz)

    # Format the localized datetime object to a string
    return localized_dt.strftime('%Y-%m-%d %I:%M:%S %p')


def get_serializer(data={}):
    return {
        **data,
    }


class MockSpace:

    def __init__(self, meeting_uri):
        self.meeting_uri = meeting_uri


@pytest.fixture(autouse=True)
def meeting_url(db, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
    url = fake.url()
    monkeypatch.setattr(actions, 'send_email_message', MagicMock())
    monkeypatch.setattr(GoogleMeet, '__init__', MagicMock(return_value=None))
    monkeypatch.setattr(GoogleMeet, 'end_active_conference', MagicMock(return_value=MockSpace(url)))
    monkeypatch.setattr(Logger, 'error', MagicMock())
    monkeypatch.setattr(Logger, 'warn', MagicMock())
    yield url


@pytest.fixture
def tz(fake: capy.Fake):
    yield fake.timezone()


@pytest.fixture
def questions_and_answers(fake: capy.Fake):
    yield [{'question': fake.name(), 'answer': fake.text()} for _ in range(3)]


@pytest.mark.parametrize('mentorship_session, mentorship_service', [
    (0, 0),
    (1, 0),
    (0, 1),
    (1, {
        'video_provider': 'DAILY'
    }),
])
def test_no_session(database: capy.Database, mentorship_session, mentorship_service):
    database.create(mentorship_session=mentorship_session, mentorship_service=mentorship_service, city=1, country=1)

    cancellate_conference_on_google_meet.delay(1)

    assert actions.send_email_message.call_args_list == []
    assert GoogleMeet.end_active_conference.call_args_list == []
    assert Logger.error.call_args_list == [
        call('Mentorship session 1 not found', exc_info=True),
    ]
    assert Logger.warn.call_args_list == []


def test_session__same_lang(database: capy.Database, meeting_url: str, utc_now: datetime, tz: str):
    model = database.create(user=2,
                            mentorship_session={
                                'starts_at': utc_now,
                                'ends_at': utc_now + timedelta(hours=1),
                            },
                            mentorship_service={'video_provider': 'GOOGLE_MEET'},
                            city=1,
                            country=1,
                            academy={'timezone': tz},
                            mentor_profile={'user_id': 2},
                            user_setting=[{
                                'lang': 'en',
                                'user_id': n + 1,
                            } for n in range(2)])

    cancellate_conference_on_google_meet.delay(1)

    title = (f'{model.mentorship_session.service.name} {model.mentorship_session.id} | '
             f'{model.user[1].first_name} {model.user[1].last_name} | '
             f'{model.user[0].first_name} {model.user[0].last_name}')

    assert GoogleMeet.end_active_conference.call_args_list == [call(name=title)]
    assert Logger.error.call_args_list == []
    assert Logger.warn.call_args_list == []

    assert actions.send_email_message.call_args_list == [
        call(
            'meet_notification',
            [model.user[1].email, model.user[0].email],
            {
                'title':
                model.mentorship_service.name,
                'description':
                model.mentorship_service.description,
                'meet': {
                    'url': meeting_url,
                    'cancellation_url': f'/mentor/session/{model.mentorship_session.id}/cancel',
                    'date': model.mentorship_session.starts_at.isoformat(),
                    'preformatted_date': localize_datetime(model.academy, model.mentorship_session.starts_at),
                    'duration': model.mentorship_session.ends_at - model.mentorship_session.starts_at,
                },
                'organizers': [
                    {
                        'name': f'{model.user[1].first_name} {model.user[1].last_name}',
                    },
                ],
                'invitees': [
                    {
                        'name': f'{model.user[0].first_name} {model.user[0].last_name}',
                        'email': model.user[0].email
                    },
                ],
                'answers': [],
                'translations': {
                    'organizers': 'Organizers',
                    'invitees': 'Invitees',
                    'date': 'Date',
                    'duration': 'Duration',
                    'location': 'Location',
                    'enter': 'Enter',
                    'cancel': 'Cancel',
                    'details': 'Details',
                    'qaa': 'Questions and Answers'
                },
            },
        )
    ]


def test_session__both_langs__with_answers(database: capy.Database, meeting_url: str,
                                           questions_and_answers: dict[str, str], utc_now: datetime, tz: str):
    model = database.create(user=2,
                            mentorship_session={
                                'questions_and_answers': questions_and_answers,
                                'starts_at': utc_now,
                                'ends_at': utc_now + timedelta(hours=1),
                            },
                            mentorship_service={'video_provider': 'GOOGLE_MEET'},
                            city=1,
                            country=1,
                            academy={'timezone': tz},
                            mentor_profile={'user_id': 2},
                            user_setting=[
                                {
                                    'lang': 'es',
                                    'user_id': 1,
                                },
                                {
                                    'lang': 'en',
                                    'user_id': 2,
                                },
                            ])

    cancellate_conference_on_google_meet.delay(1)

    title = (f'{model.mentorship_session.service.name} {model.mentorship_session.id} | '
             f'{model.user[1].first_name} {model.user[1].last_name} | '
             f'{model.user[0].first_name} {model.user[0].last_name}')

    assert GoogleMeet.end_active_conference.call_args_list == [call(name=title)]
    assert Logger.error.call_args_list == []
    assert Logger.warn.call_args_list == []

    assert actions.send_email_message.call_args_list == [
        call(
            'meet_notification',
            [model.user[1].email],
            {
                'title':
                model.mentorship_service.name,
                'description':
                model.mentorship_service.description,
                'meet': {
                    'url': meeting_url,
                    'cancellation_url': f'/mentor/session/{model.mentorship_session.id}/cancel',
                    'date': model.mentorship_session.starts_at.isoformat(),
                    'preformatted_date': localize_datetime(model.academy, model.mentorship_session.starts_at),
                    'duration': model.mentorship_session.ends_at - model.mentorship_session.starts_at,
                },
                'organizers': [
                    {
                        'name': f'{model.user[1].first_name} {model.user[1].last_name}',
                    },
                ],
                'invitees': [
                    {
                        'name': f'{model.user[0].first_name} {model.user[0].last_name}',
                        'email': model.user[0].email
                    },
                ],
                'answers':
                questions_and_answers,
                'translations': {
                    'organizers': 'Organizers',
                    'invitees': 'Invitees',
                    'date': 'Date',
                    'duration': 'Duration',
                    'location': 'Location',
                    'enter': 'Enter',
                    'cancel': 'Cancel',
                    'details': 'Details',
                    'qaa': 'Questions and Answers',
                },
            },
        ),
        call(
            'meet_notification',
            [model.user[0].email],
            {
                'title':
                model.mentorship_service.name,
                'description':
                model.mentorship_service.description,
                'meet': {
                    'url': meeting_url,
                    'cancellation_url': f'/mentor/session/{model.mentorship_session.id}/cancel',
                    'date': model.mentorship_session.starts_at.isoformat(),
                    'preformatted_date': localize_datetime(model.academy, model.mentorship_session.starts_at),
                    'duration': model.mentorship_session.ends_at - model.mentorship_session.starts_at,
                },
                'organizers': [
                    {
                        'name': f'{model.user[1].first_name} {model.user[1].last_name}',
                    },
                ],
                'invitees': [
                    {
                        'name': f'{model.user[0].first_name} {model.user[0].last_name}',
                        'email': model.user[0].email
                    },
                ],
                'answers':
                questions_and_answers,
                'translations': {
                    'organizers': 'Organizadores',
                    'invitees': 'Invitados',
                    'date': 'Fecha',
                    'duration': 'Duración',
                    'location': 'Ubicación',
                    'enter': 'Entrar',
                    'cancel': 'Cancelar',
                    'details': 'Detalles',
                    'qaa': 'Preguntas y Respuestas',
                },
            },
        ),
    ]
