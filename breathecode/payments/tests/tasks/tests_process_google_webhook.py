"""
Test /answer
"""

import base64
import hashlib
import hmac
import json
import os
import random
from datetime import timedelta
from logging import Logger
from typing import Callable
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from capyc.core.object import Object
from django.utils import timezone
from task_manager.core.exceptions import AbortTask

from breathecode.payments import tasks
from breathecode.tests.mixins.breathecode_mixin import Breathecode

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, conference_record_patcher):
    # mock logger with monkeypatch

    monkeypatch.setenv("GOOGLE_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr("logging.Logger.info", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("task_manager.django.tasks.execute_signal.delay", MagicMock())

    monkeypatch.setattr("breathecode.services.google_meet.GoogleMeet.__init__", MagicMock(return_value=None))
    # monkeypatch.setattr(
    #     "breathecode.services.google_meet.GoogleMeet.get_conference_record",
    #     MagicMock(
    #         return_value=Object(space="https://meet.google.com/fake", meeting_uri="https://meet.google.com/fake")
    #     ),
    # )
    monkeypatch.setattr(
        "breathecode.services.google_meet.GoogleMeet.get_space",
        MagicMock(return_value=Object(meeting_uri="https://meet.google.com/fake")),
    )
    monkeypatch.setattr(
        "breathecode.services.google_meet.GoogleMeet.get_participant_session",
        MagicMock(return_value=Object(start_time=UTC_NOW, end_time=UTC_NOW + timedelta(hours=1))),
    )

    conference_record_patcher(
        {
            "start_time": UTC_NOW,
            "end_time": None,
        }
    )

    yield


def serialize_participant_object(data: dict):
    for key in data:
        if isinstance(data[key], dict):
            data[key] = serialize_participant_object(data[key])

    return Object(**data)


@pytest.fixture
def participant_patcher(monkeypatch: pytest.MonkeyPatch):
    def patcher(data: dict):
        monkeypatch.setattr(
            "breathecode.services.google_meet.GoogleMeet.get_participant",
            MagicMock(return_value=serialize_participant_object(data)),
        )

    yield patcher


@pytest.fixture
def conference_record_patcher(monkeypatch: pytest.MonkeyPatch):
    def patcher(data: dict):
        monkeypatch.setattr(
            "breathecode.services.google_meet.GoogleMeet.get_conference_record",
            MagicMock(
                return_value=serialize_participant_object(
                    {
                        "space": "https://meet.google.com/fake",
                        "meeting_uri": "https://meet.google.com/fake",
                        **data,
                    }
                )
            ),
        )

    yield patcher


def serialize(data: dict):
    x = json.dumps(data)
    message = base64.b64encode(x.encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        key=os.getenv("GOOGLE_WEBHOOK_SECRET").encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256
    ).hexdigest()

    return {
        "data": message,
        "signature": signature,
    }


def test_not_found(bc: Breathecode):

    tasks.process_google_webhook(1)

    assert bc.database.list_of("authenticate.GoogleWebhook") == []

    assert Logger.info.call_args_list == [
        call("Starting process_google_webhook for id 1"),
        call("Starting process_google_webhook for id 1"),
    ]
    assert Logger.error.call_args_list == [
        call("GoogleWebhook with id 1 not found", exc_info=True),
    ]


def test_no_credentials(database: capy.Database, format: capy.Format):
    data = serialize({"credential_id": "123456"})

    model = database.create(google_webhook={"message": data["data"]})

    tasks.process_google_webhook(1)

    assert database.list_of("authenticate.GoogleWebhook") == [
        format.to_obj_repr(model.google_webhook),
    ]

    assert Logger.info.call_args_list == [
        call("Starting process_google_webhook for id 1"),
    ]
    assert Logger.error.call_args_list == [
        call("CredentialsGoogle not found", exc_info=True),
    ]


def test_action_not_found(database: capy.Database, format: capy.Format):
    data = serialize({"credential_id": "123456"})

    model = database.create(
        google_webhook={"message": data["data"]},
        credentials_google=1,
        user=1,
        academy_auth_settings=1,
        city=1,
        country=1,
    )

    tasks.process_google_webhook(1)

    assert database.list_of("authenticate.GoogleWebhook") == [
        format.to_obj_repr(model.google_webhook),
    ]

    assert Logger.info.call_args_list == [
        call("Starting process_google_webhook for id 1"),
    ]
    assert Logger.error.call_args_list == [
        call("Action credential_id not found", exc_info=True),
    ]


class TestConferenceRecord:
    def test_no_session(self, database: capy.Database, format: capy.Format):
        data = serialize({"conferenceRecord": {"name": "123456"}})

        model = database.create(
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "ERROR",
                "status_text": "MentorshipSession with meeting url https://meet.google.com/fake not found",
                "type": "conferenceRecord",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == []

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == [
            call("MentorshipSession with meeting url https://meet.google.com/fake not found", exc_info=True),
        ]

    def test_starting_session(
        self,
        database: capy.Database,
        format: capy.Format,
        conference_record_patcher: Callable,
    ):
        data = serialize({"conferenceRecord": {"name": "123456"}})

        conference_record_patcher(
            {
                "start_time": UTC_NOW,
                "end_time": None,
            }
        )

        model = database.create(
            mentorship_session={
                "online_meeting_url": "https://meet.google.com/fake",
            },
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "conferenceRecord",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "STARTED",
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []

    @pytest.mark.parametrize(
        "started_at,mentor_joined_at",
        [
            (None, UTC_NOW),
            (UTC_NOW, None),
        ],
    )
    def test_someone_dont_show_up(
        self,
        database: capy.Database,
        format: capy.Format,
        conference_record_patcher: Callable,
        started_at,
        mentor_joined_at,
    ):
        data = serialize({"conferenceRecord": {"name": "123456"}})

        conference_record_patcher(
            {
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={
                "online_meeting_url": "https://meet.google.com/fake",
                "started_at": started_at,
                "mentor_joined_at": mentor_joined_at,
            },
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "conferenceRecord",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "FAILED",
                "ended_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []

    def test_everyone_show_up(
        self,
        database: capy.Database,
        format: capy.Format,
        conference_record_patcher: Callable,
    ):
        data = serialize({"conferenceRecord": {"name": "123456"}})

        conference_record_patcher(
            {
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={
                "online_meeting_url": "https://meet.google.com/fake",
                "started_at": UTC_NOW,
                "mentor_joined_at": UTC_NOW,
            },
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "conferenceRecord",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "COMPLETED",
                "ended_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []


class TestParticipantSession:
    def test_no_session(self, database: capy.Database, format: capy.Format, participant_patcher: Callable):
        data = serialize({"participantSession": {"name": "asd/123456/asd/123456"}})

        participant_patcher(
            {
                "signedin_user": None,
            }
        )

        model = database.create(
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "ERROR",
                "status_text": "MentorshipSession with meeting url https://meet.google.com/fake not found",
                "type": "participantSession",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == []

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == [
            call("MentorshipSession with meeting url https://meet.google.com/fake not found", exc_info=True),
        ]

    @pytest.mark.parametrize("signedin_user", [None, {"user": 123123}])
    def test_mentee(
        self,
        database: capy.Database,
        format: capy.Format,
        participant_patcher: Callable,
        signedin_user: dict | None,
    ):
        data = serialize({"participantSession": {"name": "asd/123456/asd/123456"}})

        participant_patcher(
            {
                "signedin_user": signedin_user,
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={"online_meeting_url": "https://meet.google.com/fake"},
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "participantSession",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "PENDING",
                "started_at": UTC_NOW,
                "mentee_left_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []

    @pytest.mark.parametrize("signedin_user", [None, {"user": 123123}])
    def test_mentee__dont_override_started_at__override_mentee_left_at(
        self,
        database: capy.Database,
        format: capy.Format,
        participant_patcher: Callable,
        signedin_user: dict | None,
    ):
        data = serialize({"participantSession": {"name": "asd/123456/asd/123456"}})

        participant_patcher(
            {
                "signedin_user": signedin_user,
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={
                "online_meeting_url": "https://meet.google.com/fake",
                "started_at": UTC_NOW - timedelta(minutes=30),
                "mentee_left_at": UTC_NOW + timedelta(minutes=30),
            },
            google_webhook={"message": data["data"]},
            credentials_google=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "participantSession",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "PENDING",
                "started_at": UTC_NOW - timedelta(minutes=30),
                "mentee_left_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []

    def test_mentor(
        self,
        database: capy.Database,
        format: capy.Format,
        participant_patcher: Callable,
    ):
        data = serialize({"participantSession": {"name": "asd/123456/asd/123456"}})

        participant_patcher(
            {
                "signedin_user": {"user": 123123},
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={"online_meeting_url": "https://meet.google.com/fake"},
            google_webhook={"message": data["data"]},
            credentials_google={"google_id": 123123},
            mentor_profile=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "participantSession",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "PENDING",
                "mentor_joined_at": UTC_NOW,
                "mentor_left_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []

    def test_mentor__dont_override_joined_at__override_left_at(
        self,
        database: capy.Database,
        format: capy.Format,
        participant_patcher: Callable,
    ):
        data = serialize({"participantSession": {"name": "asd/123456/asd/123456"}})

        participant_patcher(
            {
                "signedin_user": {"user": 123123},
                "start_time": UTC_NOW,
                "end_time": UTC_NOW + timedelta(hours=1),
            }
        )

        model = database.create(
            mentorship_session={
                "online_meeting_url": "https://meet.google.com/fake",
                "mentor_joined_at": UTC_NOW - timedelta(minutes=30),
                "mentor_left_at": UTC_NOW + timedelta(minutes=30),
            },
            google_webhook={"message": data["data"]},
            credentials_google={"google_id": 123123},
            mentor_profile=1,
            user=1,
            academy_auth_settings=1,
            city=1,
            country=1,
        )

        tasks.process_google_webhook(1)

        assert database.list_of("authenticate.GoogleWebhook") == [
            {
                **format.to_obj_repr(model.google_webhook),
                "status": "DONE",
                "type": "participantSession",
            },
        ]
        assert database.list_of("mentorship.MentorshipSession") == [
            {
                **format.to_obj_repr(model.mentorship_session),
                "status": "PENDING",
                "mentor_joined_at": UTC_NOW - timedelta(minutes=30),
                "mentor_left_at": UTC_NOW + timedelta(hours=1),
            },
        ]

        assert Logger.info.call_args_list == [
            call("Starting process_google_webhook for id 1"),
        ]
        assert Logger.error.call_args_list == []
