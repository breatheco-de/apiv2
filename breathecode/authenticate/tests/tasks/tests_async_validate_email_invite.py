import logging
import random
from unittest.mock import MagicMock, call

import pytest

from breathecode.authenticate.tasks import async_validate_email_invite
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("logging.Logger.error", MagicMock())
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


@pytest.fixture
def custom_res(patch_request):

    def wrapper(data={}):
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
            **data,
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

    return wrapper


@pytest.fixture
def error_res(patch_request):
    validation_res = {
        "success": False,
        "error": {
            "code": 210,
            "type": "no_email_address_supplied",
            "info": "Please specify an email address. [Example: support@apilayer.com]",
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


@pytest.fixture
def exception_res(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("requests.get", MagicMock(side_effect=Exception("random error")))
    yield


def test_no_invites(database: capy.Database):
    async_validate_email_invite.delay(1)

    assert database.list_of("authenticate.UserInvite") == []
    assert database.list_of("auth.User") == []

    assert logging.Logger.error.call_args_list == [
        call("UserInvite 1 not found", exc_info=True),
    ]


def test_throws_exception(database: capy.Database, format: capy.Format, exception_res):
    model = database.create(user_invite={"email": "pokemon@potato.io"})

    async_validate_email_invite.delay(1)

    assert database.list_of("authenticate.UserInvite") == [
        format.to_obj_repr(model.user_invite),
    ]
    assert database.list_of("auth.User") == []
    assert logging.Logger.error.call_args_list == [
        call("Retrying email validation for invite 1", exc_info=True),
        call("Retrying email validation for invite 1", exc_info=True),
    ]


def test_bad_response(database: capy.Database, format: capy.Format, error_res):
    model = database.create(user_invite={"email": "pokemon@potato.io"})

    async_validate_email_invite.delay(1)

    assert database.list_of("authenticate.UserInvite") == [
        {
            **format.to_obj_repr(model.user_invite),
            "process_message": "email-validation-error",
            "process_status": "ERROR",
            "status": "REJECTED",
        },
    ]
    assert database.list_of("auth.User") == []
    assert logging.Logger.error.call_args_list == []


@pytest.mark.parametrize(
    "data, error",
    [
        (
            {
                "is_disposable_email": {
                    "value": True,
                },
            },
            "disposable-email",
        ),
        (
            {
                "is_mx_found": {
                    "value": False,
                },
            },
            "invalid-email",
        ),
        (
            {
                "quality_score": 0.59,
            },
            "poor-quality-email",
        ),
    ],
)
def test_invalid_email_response(database: capy.Database, format: capy.Format, custom_res, data, error):
    custom_res(data)
    model = database.create(user_invite={"email": "pokemon@potato.io"})

    async_validate_email_invite.delay(1)

    assert database.list_of("authenticate.UserInvite") == [
        {
            **format.to_obj_repr(model.user_invite),
            "process_message": error,
            "process_status": "ERROR",
            "status": "REJECTED",
        },
    ]
    assert database.list_of("auth.User") == []
    assert logging.Logger.error.call_args_list == []


def test_good_response(database: capy.Database, format: capy.Format, validation_res):
    model = database.create(user_invite={"email": "pokemon@potato.io"})

    async_validate_email_invite.delay(1)

    assert database.list_of("authenticate.UserInvite") == [
        {
            **format.to_obj_repr(model.user_invite),
            "email_quality": validation_res["quality_score"],
            "email_status": {
                "catch_all": validation_res["is_catchall_email"]["value"],
                "disposable": validation_res["is_disposable_email"]["value"],
                "domain": "potato.io",
                "email": "pokemon@potato.io",
                "format_valid": validation_res["is_valid_format"]["value"],
                "free": validation_res["is_free_email"]["value"],
                "mx_found": validation_res["is_mx_found"]["value"],
                "role": validation_res["is_role_email"]["value"],
                "smtp_check": validation_res["is_smtp_valid"]["value"],
                "score": validation_res["quality_score"],
                "user": "pokemon",
            },
        },
    ]
    assert database.list_of("auth.User") == []
    assert logging.Logger.error.call_args_list == []
