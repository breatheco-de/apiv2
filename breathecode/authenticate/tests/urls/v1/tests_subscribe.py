"""
Test /v1/auth/subscribe
"""

import hashlib
import os
import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from breathecode.authenticate.models import Token
from breathecode.authenticate.tasks import async_validate_email_invite
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

now = timezone.now()


def user_db_item(data={}):
    return {
        "email": "",
        "first_name": "",
        "id": 0,
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "last_login": None,
        "last_name": "",
        "password": "",
        "username": "",
        **data,
    }


def plan_db_item(plan, data={}):
    return {
        "id": plan.id,
        "event_type_set_id": plan.event_type_set.id if plan.event_type_set else None,
        "mentorship_service_set_id": plan.mentorship_service_set.id if plan.mentorship_service_set else None,
        "cohort_set_id": plan.cohort_set.id if plan.cohort_set else None,
        "currency_id": plan.currency.id,
        "slug": plan.slug,
        "status": plan.status,
        "has_waiting_list": plan.has_waiting_list,
        "is_onboarding": plan.is_onboarding,
        "time_of_life": plan.time_of_life,
        "time_of_life_unit": plan.time_of_life_unit,
        "trial_duration": plan.trial_duration,
        "trial_duration_unit": plan.trial_duration_unit,
        "is_renewable": plan.is_renewable,
        "owner_id": plan.owner.id if plan.owner else None,
        "price_per_half": plan.price_per_half,
        "price_per_month": plan.price_per_month,
        "price_per_quarter": plan.price_per_quarter,
        "price_per_year": plan.price_per_year,
        **data,
    }


def user_invite_db_item(data={}):
    return {
        "academy_id": None,
        "author_id": None,
        "cohort_id": None,
        "id": 1,
        "role_id": None,
        "sent_at": None,
        "status": "PENDING",
        "conversion_info": None,
        "has_marketing_consent": False,
        "event_slug": None,
        "asset_slug": None,
        "is_email_validated": False,
        "token": "",
        "process_message": "",
        "process_status": "PENDING",
        "syllabus_id": None,
        "user_id": None,
        "city": None,
        "email": "pokemon@potato.io",
        "email_quality": None,
        "email_status": None,
        "country": None,
        "first_name": None,
        "last_name": None,
        "latitude": None,
        "longitude": None,
        "expires_at": None,
        "phone": "",
        **data,
    }


def plan_serializer(plan):
    return {
        "financing_options": [],
        "service_items": [],
        "has_available_cohorts": bool(plan.cohort_set),
        "slug": plan.slug,
        "status": plan.status,
        "time_of_life": plan.time_of_life,
        "time_of_life_unit": plan.time_of_life_unit,
        "trial_duration": plan.trial_duration,
        "trial_duration_unit": plan.trial_duration_unit,
    }


def post_serializer(plans=[], academy=None, data={}):
    return {
        "id": 0,
        "academy": academy.id if academy else None,
        "access_token": None,
        "cohort": None,
        "syllabus": None,
        "email": "",
        "first_name": "",
        "last_name": "",
        "phone": "",
        "plans": [plan_serializer(plan) for plan in plans],
        "city": None,
        "country": None,
        "latitude": None,
        "longitude": None,
        "conversion_info": None,
        "asset_slug": None,
        "event_slug": None,
        "has_marketing_consent": False,
        **data,
    }


def put_serializer(user_invite, cohort=None, syllabus=None, user=None, academy=None, plans=[], data={}):
    return {
        "id": user_invite.id,
        "access_token": None,
        "academy": academy.id if academy else None,
        "cohort": cohort.id if cohort else None,
        "syllabus": syllabus.id if syllabus else None,
        "email": user_invite.email,
        "first_name": user_invite.first_name,
        "last_name": user_invite.last_name,
        "phone": user_invite.phone,
        "user": user.id if user else None,
        "plans": [plan_serializer(plan) for plan in plans],
        "city": None,
        "country": None,
        "latitude": None,
        "longitude": None,
        "conversion_info": None,
        "asset_slug": None,
        "event_slug": None,
        "status": user_invite.status,
        "has_marketing_consent": False,
        **data,
    }


b = os.urandom(16)


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch, db):

    monkeypatch.setattr("os.urandom", lambda _: b)
    monkeypatch.setattr("breathecode.authenticate.tasks.create_user_from_invite.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.async_validate_email_invite.delay", MagicMock())
    monkeypatch.setattr("breathecode.authenticate.tasks.verify_user_invite_email.delay", MagicMock())

    yield


@pytest.fixture
def validation_res(patch_request):
    validation_res = {
        "quality_score": (random.random() * 0.4) + 0.6,
        "email_quality": (random.random() * 0.4) + 0.6,
        "is_valid_format": {
            "value": True,
        },
        "is_mx_found": {
            "value": True,
        },
        "is_smtp_valid": {
            "value": True,
        },
        "is_catchall_email": {
            "value": True,
        },
        "is_role_email": {
            "value": True,
        },
        "is_disposable_email": {
            "value": False,
        },
        "is_free_email": {
            "value": True,
        },
    }
    patch_request(
        [
            (
                call(
                    "get",
                    "https://emailvalidation.abstractapi.com/v1/?api_key=None&email=pokemon@potato.io",
                    params=None,
                    timeout=10,
                ),
                validation_res,
            ),
        ]
    )
    return validation_res


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__without_email(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:subscribe")
    response = client.post(url)

    json = response.json()
    expected = {"detail": "without-email", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == []
    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


# """
# 🔽🔽🔽 Post without UserInvite
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__without_user_invite(bc: Breathecode, client: APIClient, validation_res):
    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io", "first_name": "lord", "last_name": "valdomero", "phone": "+123123123"}

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    json = response.json()
    expected = post_serializer(
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]


# """
# 🔽🔽🔽 Post without UserInvite with Asset slug
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__without_user_invite_with_asset_slug(bc: Breathecode, client: APIClient, validation_res):
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "asset_slug": "pokemon_exercise",
    }

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    json = response.json()
    expected = post_serializer(
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]


# """
# 🔽🔽🔽 Post without UserInvite with Event slug
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__without_user_invite_with_event_slug(bc: Breathecode, client: APIClient, validation_res):
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "event_slug": "pokemon_event",
    }

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    json = response.json()
    expected = post_serializer(
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]


# """
# 🔽🔽🔽 Post with UserInvite
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__already_exists__status_waiting_list(bc: Breathecode, client: APIClient):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "pokemon@potato.io", "status": "WAITING_LIST"}
    model = bc.database.create(user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "user-invite-exists", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__already_exists__status_pending__academy_no_saas(
    bc: Breathecode, client: APIClient
):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "pokemon@potato.io", "status": "PENDING"}
    academy = {"available_as_saas": False}
    model = bc.database.create(user_invite=user_invite, academy=academy)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "invite-exists", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__already_exists__status_pending__academy_no_saas__from_cohort(
    bc: Breathecode, client: APIClient
):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "pokemon@potato.io", "status": "PENDING", "academy_id": None}
    academy = {"available_as_saas": False}
    model = bc.database.create(user_invite=user_invite, academy=academy, cohort=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "invite-exists", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__already_exists__status_pending(bc: Breathecode, client: APIClient):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invites = [{"email": "pokemon@potato.io", "status": x} for x in ["PENDING", "ACCEPTED"]]
    model = bc.database.create(user_invite=user_invites)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {"detail": "user-invite-exists-status-pending", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == bc.format.to_dict(model.user_invite)

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__already_exists__status_accepted(bc: Breathecode, client: APIClient):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "pokemon@potato.io", "status": "ACCEPTED"}
    model = bc.database.create(user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {
        "detail": "user-invite-exists-status-accepted",
        "status_code": 400,
        "silent": True,
        "silent_code": "user-invite-exists-status-accepted",
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


# """
# 🔽🔽🔽 Post with UserInvite
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
def test_task__post__with_user_invite__user_exists(bc: Breathecode, client: APIClient):
    """
    Descriptions of models are being generated:

        User(id=1):
        groups: []
        user_permissions: []
    """

    user = {"email": "pokemon@potato.io"}
    model = bc.database.create(user=user)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io"}
    response = client.post(url, data, format="json")

    json = response.json()
    expected = {
        "detail": "user-exists",
        "silent": True,
        "silent_code": "user-exists",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == []
    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []


# """
# 🔽🔽🔽 Post with UserInvite with other email
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__post__with_user_invite(bc: Breathecode, client: APIClient, validation_res):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "henrrieta@horseman.io", "status": "WAITING_LIST"}
    model = bc.database.create(user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {"email": "pokemon@potato.io", "first_name": "lord", "last_name": "valdomero", "phone": "+123123123"}

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    json = response.json()
    expected = post_serializer(
        data={
            "id": 2,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        }
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            data={
                "id": 2,
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1), call(2)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    2,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Post does not get in waiting list using a plan
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__post__does_not_get_in_waiting_list_using_a_plan(bc: Breathecode, client: APIClient, validation_res):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "henrrieta@horseman.io", "status": "WAITING_LIST"}
    plan = {"time_of_life": None, "time_of_life_unit": None, "has_waiting_list": True, "invites": []}
    model = bc.database.create(user_invite=user_invite, plan=plan)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "plan": 1,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["plan"]
    json = response.json()
    expected = put_serializer(
        model.user_invite,
        plans=[model.plan],
        data={
            "id": 2,
            **data,
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            data={
                "id": 2,
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "PENDING",
                "status": "WAITING_LIST",
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                "email_quality": None,
                "email_status": None,
                **data,
            }
        ),
    ]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == [plan_db_item(model.plan, data={})]
    bc.check.queryset_with_pks(model.plan.invites.all(), [2])
    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Post get in waiting list using a plan
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__post__get_in_waiting_list_using_a_plan(bc: Breathecode, client: APIClient, validation_res):
    """
    Descriptions of models are being generated:

        UserInvite(id=1): {}
    """

    user_invite = {"email": "henrrieta@horseman.io", "status": "WAITING_LIST"}
    plan = {"time_of_life": None, "time_of_life_unit": None, "has_waiting_list": False, "invites": []}
    model = bc.database.create(user_invite=user_invite, plan=plan)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "plan": 1,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["plan"]
    json = response.json()
    expected = post_serializer(
        plans=[model.plan],
        data={
            "id": 2,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            data={
                "id": 2,
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == [plan_db_item(model.plan, data={})]
    bc.check.queryset_with_pks(model.plan.invites.all(), [2])

    token = hashlib.sha512("pokemon@potato.io".encode("UTF-8") + b).hexdigest()
    assert async_validate_email_invite.delay.call_args_list == [call(1), call(2)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    2,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    User = bc.database.get_model("auth.User")
    user = User.objects.get(email=data["email"])

    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# When: Syllabus is passed and does not exist
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__syllabus_does_not_exists(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": random.choice([bc.fake.slug(), random.randint(1, 100)]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["syllabus"]
    json = response.json()
    expected = {"detail": "syllabus-not-found", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == []

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# When: Course is passed and does not exist
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__course_does_not_exists(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([bc.fake.slug(), random.randint(1, 100)]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]
    json = response.json()
    expected = {"detail": "course-not-found", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == []

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Course
# When: Course is passed as slug and exists
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__course_without_syllabus(bc: Breathecode, client: APIClient, validation_res):
    model = bc.database.create(course=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]
    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "DONE",
                "status": "ACCEPTED",
                "academy_id": 1,
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    del data["phone"]
    users = [x for x in bc.database.list_of("auth.User") if x.pop("date_joined")]

    users == [
        user_db_item(
            data={
                **data,
                "id": 1,
                "username": "pokemon@potato.io",
            }
        ),
    ]
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []

    token = hashlib.sha512("pokemon@potato.io".encode("UTF-8") + b).hexdigest()
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    User = bc.database.get_model("auth.User")
    user = User.objects.get(email=data["email"])

    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Given: 1 Course
# When: Course is passed as slug and exists
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__course_and_syllabus(bc: Breathecode, client: APIClient, validation_res):
    model = bc.database.create(course=1, syllabus=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]
    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    token = hashlib.sha512("pokemon@potato.io".encode("UTF-8") + b).hexdigest()

    data["syllabus_id"] = data.pop("syllabus")
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                **data,
            }
        )
    ]

    del data["phone"]
    del data["syllabus_id"]
    users = [x for x in bc.database.list_of("auth.User") if x.pop("date_joined")]

    users == [
        user_db_item(
            data={
                **data,
                "id": 1,
                "username": "pokemon@potato.io",
            }
        ),
    ]
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    User = bc.database.get_model("auth.User")
    user = User.objects.get(email=data["email"])

    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Given: 1 Course and 1 Syllabus
# When: Course is passed as slug and exists, course is not associated to syllabus
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__course_and_syllabus__syllabus_not_associated_to_course(bc: Breathecode, client: APIClient):
    course = {"syllabus": []}
    syllabus = {"slug": bc.fake.slug()}
    model = bc.database.create(course=course, syllabus=syllabus)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
        # 'token': token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]

    json = response.json()
    expected = {"detail": "syllabus-not-belong-to-course", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    del data["syllabus"]

    assert bc.database.list_of("authenticate.UserInvite") == []

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [])
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Course, 1 Syllabus
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__course_and_syllabus__waiting_list(bc: Breathecode, client: APIClient):
    course = {"has_waiting_list": True, "invites": []}
    model = bc.database.create(course=course, syllabus=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": None,
            "user": None,
            **data,
            "status": "WAITING_LIST",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    data["syllabus_id"] = data.pop("syllabus")
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "PENDING",
                "status": "WAITING_LIST",
                "academy_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    del data["phone"]
    del data["syllabus_id"]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Course, 1 UserInvite and 1 Syllabus
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__with_other_invite__course_and_syllabus__waiting_list(bc: Breathecode, client: APIClient):
    course = {"has_waiting_list": True, "invites": []}
    user_invite = {"email": "pokemon@potato.io", "status": "WAITING_LIST"}
    model = bc.database.create(course=course, syllabus=1, user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["course"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 2,
            "access_token": None,
            "user": None,
            **data,
            "status": "WAITING_LIST",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    data["syllabus_id"] = data.pop("syllabus")
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "PENDING",
                "status": "WAITING_LIST",
                "academy_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
                "id": 2,
            }
        ),
    ]

    del data["phone"]
    del data["syllabus_id"]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [2])
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Plan and 1 UserInvite
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__with_other_invite__plan__waiting_list(bc: Breathecode, client: APIClient):
    plan = {"has_waiting_list": True, "invites": [], "time_of_life": None, "time_of_life_unit": None}
    user_invite = {"email": "pokemon@potato.io", "status": "WAITING_LIST"}
    model = bc.database.create(plan=plan, user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "plan": random.choice([model.plan.id, model.plan.slug]),
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["plan"]

    json = response.json()
    expected = post_serializer(
        plans=[model.plan],
        data={
            "id": 2,
            "access_token": None,
            "user": None,
            **data,
            "status": "WAITING_LIST",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    # data['syllabus_id'] = data.pop('syllabus')
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            data={
                "token": hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest(),
                "process_status": "PENDING",
                "status": "WAITING_LIST",
                "academy_id": None,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
                "id": 2,
            }
        ),
    ]

    del data["phone"]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("payments.Plan") == [
        bc.format.to_dict(model.plan),
    ]

    bc.check.queryset_with_pks(model.plan.invites.all(), [2])
    assert bc.database.list_of("marketing.Course") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Cohort and 1 UserInvite
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__with_other_invite__cohort__waiting_list(bc: Breathecode, client: APIClient, validation_res):
    user_invite = {"email": "pokemon@potato.io", "status": "WAITING_LIST", "cohort_id": None, "syllabus_id": None}
    model = bc.database.create(cohort=1, user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "cohort": model.cohort.id,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["cohort"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 2,
            "access_token": access_token,
            "cohort": 1,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    token = hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest()
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            {
                "id": 2,
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                "cohort_id": 1,
                **data,
            }
        ),
    ]

    del data["phone"]

    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("marketing.Course") == []

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]
    assert async_validate_email_invite.delay.call_args_list == [call(1), call(2)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    2,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Given: 1 Syllabus and 1 UserInvite
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__post__with_other_invite__syllabus__waiting_list(bc: Breathecode, client: APIClient, validation_res):
    user_invite = {"email": "pokemon@potato.io", "status": "WAITING_LIST", "cohort_id": None, "syllabus_id": None}
    model = bc.database.create(syllabus=1, user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": model.syllabus.id,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.post(url, data, format="json")

    del data["syllabus"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        data={
            "id": 2,
            "access_token": access_token,
            "syllabus": 1,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED

    token = hashlib.sha512(("pokemon@potato.io").encode("UTF-8") + b).hexdigest()
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
        user_invite_db_item(
            {
                "id": 2,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                "syllabus_id": 1,
                **data,
            }
        ),
    ]

    del data["phone"]

    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("marketing.Course") == []

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]
    assert async_validate_email_invite.delay.call_args_list == [call(1), call(2)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    2,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Put a case syllabus not found and syllabus with course
# """
# 🔽🔽🔽 Put without email
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__without_email(bc: Breathecode, client: APIClient):
    url = reverse_lazy("authenticate:subscribe")
    response = client.put(url)

    json = response.json()
    expected = {"detail": "not-found", "status_code": 404}

    assert json == expected
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert bc.database.list_of("authenticate.UserInvite") == []
    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort as None
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__cohort_as_none(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    model = bc.database.create(user_invite=user_invite)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "token": token,
    }

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()

    expected = put_serializer(
        model.user_invite,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                **data,
            }
        )
    ]

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort not found
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__cohort_not_found(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    bc.database.create(user_invite=user_invite)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "cohort": 1,
        "token": token,
    }
    response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = {"cohort": ['Invalid pk "1" - object does not exist.']}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "status": "WAITING_LIST",
                "token": token,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("auth.User") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__cohort_found(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    model = bc.database.create(user_invite=user_invite, cohort=1)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "cohort": 1,
        "token": token,
    }

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["cohort"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                "cohort_id": 1,
                **data,
            }
        )
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__cohort_found__academy_available_as_saas__user_does_not_exists(
    bc: Breathecode, client: APIClient, validation_res
):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    academy = {"available_as_saas": True}
    model = bc.database.create(user_invite=user_invite, cohort=1, academy=academy)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "cohort": 1,
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["cohort"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                "cohort_id": 1,
                **data,
            }
        )
    ]

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User exists
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__cohort_found__academy_available_as_saas__user_exists(
    bc: Breathecode, client: APIClient, validation_res
):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    academy = {"available_as_saas": True}
    user = {"email": "pokemon@potato.io"}
    model = bc.database.create(user_invite=user_invite, cohort=1, academy=academy, user=user)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "cohort": 1,
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        user=model.user,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["cohort"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "user_id": 1,
                "token": token,
                "author_id": 1,
                "cohort_id": 1,
                **data,
            }
        )
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == [
        call(user=model.user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Syllabus not found
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__syllabus_not_found(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    bc.database.create(user_invite=user_invite)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": 1,
        "token": token,
    }
    response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = {"detail": "syllabus-not-found", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "status": "WAITING_LIST",
                "token": token,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("auth.User") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Put with UserInvite, passing Syllabus and it found
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__syllabus_found(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    model = bc.database.create(user_invite=user_invite, cohort=1, syllabus_version=1)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": 1,
        "token": token,
    }

    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()

    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["syllabus"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "syllabus_id": 1,
                "user_id": 1,
                "token": token,
                **data,
            }
        )
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Syllabus and it found, Academy available as saas, User does not exists
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__syllabus_found__academy_available_as_saas__user_does_not_exists(
    bc: Breathecode, client: APIClient, validation_res
):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    academy = {"available_as_saas": True}
    model = bc.database.create(user_invite=user_invite, cohort=1, syllabus_version=1, academy=academy)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": 1,
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["syllabus"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "syllabus_id": 1,
                "user_id": 1,
                "token": token,
                **data,
            }
        )
    ]

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Syllabus and it found, Academy available as saas, User exists
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__with_user_invite__syllabus_found__academy_available_as_saas__user_exists(
    bc: Breathecode, client: APIClient, validation_res
):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    academy = {"available_as_saas": True}
    user = {"email": "pokemon@potato.io"}
    model = bc.database.create(
        user_invite=user_invite, cohort=1, syllabus_version=1, syllabus=1, academy=academy, user=user
    )
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "syllabus": 1,
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        user=model.user,
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    del data["syllabus"]
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "academy_id": 1,
                "author_id": 1,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "syllabus_id": 1,
                "user_id": 1,
                "token": token,
                **data,
            }
        )
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    assert bc.database.list_of("auth.User") == [bc.format.to_dict(model.user)]
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == [
        call(user=model.user, token_type="login"),
    ]


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
# Plan does not exists
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__plan_does_not_exist(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    academy = {"available_as_saas": True}
    bc.database.create(user_invite=user_invite, cohort=1, academy=academy)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        # 'cohort': 1,
        "token": token,
        "plan": 1,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]

    json = response.json()
    expected = {"detail": "plan-not-found", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                "status": "WAITING_LIST",
                "academy_id": 1,
                "token": token,
                "cohort_id": 1,
            }
        ),
    ]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == []
    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert user_db == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
# Plan with has_waiting_list = True
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__plan_has_waiting_list(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
    }
    academy = {"available_as_saas": True}
    plan = {"time_of_life": None, "time_of_life_unit": None, "has_waiting_list": True, "invites": []}
    model = bc.database.create(user_invite=user_invite, academy=academy, plan=plan)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "token": token,
        "plan": 1,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["plan"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        plans=[model.plan],
        data={
            "id": 1,
            "user": None,
            **data,
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            {
                **data,
                "status": "WAITING_LIST",
                "academy_id": 1,
                "token": token,
            }
        ),
    ]

    assert bc.database.list_of("auth.User") == []

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == [plan_db_item(model.plan, data={})]
    bc.check.queryset_with_pks(model.plan.invites.all(), [1])

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# """
# 🔽🔽🔽 Put with UserInvite, passing Cohort and it found, Academy available as saas, User does not exists,
# Plan with has_waiting_list = False
# """


@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test_task__put__plan_has_not_waiting_list(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    academy = {"available_as_saas": True}
    plan = {"time_of_life": None, "time_of_life_unit": None, "has_waiting_list": False, "invites": []}
    model = bc.database.create(user_invite=user_invite, cohort=1, academy=academy, plan=plan)
    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "token": token,
        "plan": 1,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["plan"]

    json = response.json()
    expected = put_serializer(
        model.user_invite,
        academy=model.academy,
        plans=[model.plan],
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    assert bc.database.list_of("authenticate.UserInvite") == [
        {
            "user_id": 1,
            "academy_id": 1,
            "author_id": None,
            "cohort_id": None,
            "id": 1,
            "is_email_validated": False,
            "conversion_info": None,
            "has_marketing_consent": False,
            "event_slug": None,
            "asset_slug": None,
            "role_id": None,
            "sent_at": None,
            "status": "ACCEPTED",
            "process_message": "",
            "process_status": "DONE",
            "token": token,
            "syllabus_id": None,
            "city": None,
            "country": None,
            "latitude": None,
            "longitude": None,
            "email_quality": None,
            "email_status": None,
            "expires_at": None,
            **data,
        },
    ]

    user_db = bc.database.list_of("auth.User")
    for item in user_db:
        assert isinstance(item["date_joined"], datetime)
        del item["date_joined"]

    assert bc.database.list_of("marketing.Course") == []
    assert bc.database.list_of("payments.Plan") == [plan_db_item(model.plan, data={})]
    bc.check.queryset_with_pks(model.plan.invites.all(), [1])

    assert user_db == [
        {
            "email": "pokemon@potato.io",
            "first_name": "lord",
            "id": 1,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "last_login": None,
            "last_name": "valdomero",
            "password": "",
            "username": "pokemon@potato.io",
        }
    ]
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    user = bc.database.get("auth.User", 1, dict=False)
    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# When: Course is passed and does not exist
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__put__course_does_not_exists(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    model = bc.database.create(user_invite=user_invite)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([bc.fake.slug(), random.randint(1, 100)]),
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["course"]
    json = response.json()
    expected = {"detail": "course-not-found", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Course
# When: Course is passed as slug and exists
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__put__course_without_syllabus(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    model = bc.database.create(user_invite=user_invite, course=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["course"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            **data,
            "status": "ACCEPTED",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": token,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "academy_id": 1,
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    del data["phone"]
    users = [x for x in bc.database.list_of("auth.User") if x.pop("date_joined")]

    users == [
        user_db_item(
            data={
                **data,
                "id": 1,
                "username": "pokemon@potato.io",
            }
        ),
    ]
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]

    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    User = bc.database.get_model("auth.User")
    user = User.objects.get(email=data["email"])

    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Given: 1 Course
# When: Course is passed as slug and exists
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__put__course_and_syllabus(bc: Breathecode, client: APIClient, validation_res):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    model = bc.database.create(user_invite=user_invite, course=1, syllabus=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["course"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": access_token,
            "user": 1,
            "status": "ACCEPTED",
            **data,
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    data["syllabus_id"] = data.pop("syllabus")
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": token,
                "process_status": "DONE",
                "status": "ACCEPTED",
                "academy_id": 1,
                "user_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    del data["phone"]
    del data["syllabus_id"]
    users = [x for x in bc.database.list_of("auth.User") if x.pop("date_joined")]

    users == [
        user_db_item(
            data={
                **data,
                "id": 1,
                "username": "pokemon@potato.io",
            }
        ),
    ]
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []
    assert async_validate_email_invite.delay.call_args_list == [call(1)]
    assert bc.database.list_of("task_manager.ScheduledTask") == [
        {
            "arguments": {
                "args": [
                    1,
                ],
                "kwargs": {},
            },
            "duration": timedelta(days=1),
            "eta": now + timedelta(days=1),
            "id": 1,
            "status": "PENDING",
            "task_module": "breathecode.authenticate.tasks",
            "task_name": "verify_user_invite_email",
        },
    ]

    User = bc.database.get_model("auth.User")
    user = User.objects.get(email=data["email"])

    assert Token.get_or_create.call_args_list == [
        call(user=user, token_type="login"),
    ]


# Given: 1 Course and 1 Syllabus
# When: Course is passed as slug and exists, course is not associated to syllabus
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__put__course_and_syllabus__syllabus_not_associated_to_course(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    course = {"syllabus": []}
    syllabus = {"slug": bc.fake.slug()}
    model = bc.database.create(user_invite=user_invite, course=course, syllabus=syllabus)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["course"]

    json = response.json()
    expected = {"detail": "syllabus-not-belong-to-course", "status_code": 400}

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    del data["syllabus"]

    assert bc.database.list_of("authenticate.UserInvite") == [
        bc.format.to_dict(model.user_invite),
    ]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [])
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []
    assert Token.get_or_create.call_args_list == []


# Given: 1 Course, 1 UserInvite and 1 Syllabus
# When: Course is passed as slug and exists, course with waiting list
# Then: It should return 400
@patch("django.utils.timezone.now", MagicMock(return_value=now))
@patch("breathecode.authenticate.models.Token.get_or_create", MagicMock(wraps=Token.get_or_create))
def test__put__course_and_syllabus__waiting_list(bc: Breathecode, client: APIClient):
    token = bc.random.string(lower=True, upper=True, number=True, size=40)
    user_invite = {
        "email": "pokemon@potato.io",
        "status": "WAITING_LIST",
        "token": token,
        "cohort_id": None,
    }
    course = {"has_waiting_list": True, "invites": []}
    model = bc.database.create(user_invite=user_invite, course=course, syllabus=1)

    url = reverse_lazy("authenticate:subscribe")
    data = {
        "email": "pokemon@potato.io",
        "first_name": "lord",
        "last_name": "valdomero",
        "phone": "+123123123",
        "course": random.choice([model.course.id, model.course.slug]),
        "syllabus": random.choice([model.syllabus.id, model.syllabus.slug]),
        "token": token,
    }
    access_token = bc.random.string(lower=True, upper=True, number=True, size=40)
    with patch("binascii.hexlify", MagicMock(return_value=bytes(access_token, "utf-8"))):
        response = client.put(url, data, format="json")

    del data["token"]
    del data["course"]

    json = response.json()
    expected = post_serializer(
        plans=[],
        academy=model.academy,
        data={
            "id": 1,
            "access_token": None,
            "user": None,
            **data,
            "status": "WAITING_LIST",
        },
    )

    assert json == expected
    assert response.status_code == status.HTTP_200_OK

    data["syllabus_id"] = data.pop("syllabus")
    assert bc.database.list_of("authenticate.UserInvite") == [
        user_invite_db_item(
            data={
                "token": token,
                "process_status": "PENDING",
                "status": "WAITING_LIST",
                "academy_id": 1,
                "city": None,
                "country": None,
                "latitude": None,
                "longitude": None,
                **data,
            }
        ),
    ]

    del data["phone"]
    del data["syllabus_id"]

    assert bc.database.list_of("auth.User") == []
    assert bc.database.list_of("marketing.Course") == [
        bc.format.to_dict(model.course),
    ]

    bc.check.queryset_with_pks(model.course.invites.all(), [1])
    assert bc.database.list_of("payments.Plan") == []

    assert bc.database.list_of("task_manager.ScheduledTask") == []

    assert Token.get_or_create.call_args_list == []
