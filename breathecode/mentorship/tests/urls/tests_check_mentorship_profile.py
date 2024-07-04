"""
This file just can contains duck tests refert to AcademyInviteView
"""

import logging
import random
from unittest.mock import MagicMock, call

import pytest
import requests
from django.utils import timezone

from breathecode.mentorship.tasks import check_mentorship_profile
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db, monkeypatch):
    m1 = MagicMock()
    monkeypatch.setattr("logging.Logger.error", m1)
    yield m1


class ResponseMock:

    def __init__(self, status_code: int):
        self.status_code = status_code


@pytest.fixture
def mock_head_request(monkeypatch):

    def wrapper(request1=True, request2=True):
        s1 = random.randint(200, 399) if request1 else random.randint(400, 599)
        s2 = random.randint(200, 399) if request2 else random.randint(400, 599)

        request1 = ResponseMock(s1)
        request2 = ResponseMock(s2)

        m = MagicMock(side_effect=[request1, request2])

        monkeypatch.setattr(requests, "head", m)

    yield wrapper


def test_no_mentors(bc: Breathecode, mock_head_request):
    mock_head_request(request1=False, request2=False)

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == [call("Mentorship profile 1 not found", exc_info=True)]
    assert requests.head.call_args_list == []


def test_no_urls__no_syllabus(bc: Breathecode, mock_head_request):
    mock_head_request(request1=False, request2=False)

    model = bc.database.create(mentor_profile=1)

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == [
        {
            **bc.format.to_dict(model.mentor_profile),
            "availability_report": ["no-online-meeting-url", "no-booking-url", "no-syllabus"],
        }
    ]

    assert requests.head.call_args_list == []


def test_with_online_meeting_url(bc: Breathecode, fake, mock_head_request):
    mock_head_request(request1=False, request2=False)

    model = bc.database.create(mentor_profile={"online_meeting_url": fake.url()})

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == [
        {
            **bc.format.to_dict(model.mentor_profile),
            "availability_report": ["no-booking-url", "no-syllabus", "bad-online-meeting-url"],
        }
    ]

    assert requests.head.call_args_list == [
        call(model.mentor_profile.online_meeting_url, timeout=30),
    ]


def test_with_booking_url(bc: Breathecode, fake, mock_head_request):
    mock_head_request(request1=False, request2=False)

    model = bc.database.create(mentor_profile={"booking_url": "https://calendly.com/" + fake.slug()})

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == [
        {
            **bc.format.to_dict(model.mentor_profile),
            "availability_report": ["no-online-meeting-url", "no-syllabus", "bad-booking-url"],
        }
    ]

    assert requests.head.call_args_list == [
        call(model.mentor_profile.booking_url, timeout=30),
    ]


def test_with_syllabus(bc: Breathecode, fake, mock_head_request):
    mock_head_request(request1=False, request2=False)

    model = bc.database.create(mentor_profile=1, syllabus=1)

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == [
        {
            **bc.format.to_dict(model.mentor_profile),
            "availability_report": ["no-online-meeting-url", "no-booking-url"],
        }
    ]

    assert requests.head.call_args_list == []


def test_all_ok(bc: Breathecode, fake, mock_head_request):
    mock_head_request(request1=True, request2=True)

    model = bc.database.create(
        mentor_profile={
            "online_meeting_url": fake.url(),
            "booking_url": "https://calendly.com/" + fake.slug(),
        },
        syllabus=1,
    )

    check_mentorship_profile.delay(1)

    assert logging.Logger.error.call_args_list == []
    assert bc.database.list_of("mentorship.MentorProfile") == [
        {
            **bc.format.to_dict(model.mentor_profile),
            "availability_report": [],
        }
    ]

    assert requests.head.call_args_list == [
        call(model.mentor_profile.online_meeting_url, timeout=30),
        call(model.mentor_profile.booking_url, timeout=30),
    ]
