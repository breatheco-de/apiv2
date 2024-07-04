import random
from http import HTTPStatus

import pytest
from django.http.request import HttpRequest
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.core.shorteners import C
from capyc.rest_framework.exception_handler import exception_handler
from capyc.rest_framework.exceptions import PaymentException, ValidationException


def get_status_code():
    # Get all valid HTTP status codes
    valid_status_codes = [status.value for status in HTTPStatus if status.value >= 400 and status.value < 600]

    # Return a randomly chosen status code
    return random.choice(valid_status_codes)


class FakeBucketObject:

    def __init__(self, url):
        self.url = url

    def public_url(self):
        return self.url


@pytest.fixture(autouse=True)
def setup(monkeypatch, fake):

    monkeypatch.setattr("breathecode.admissions.actions.get_bucket_object", lambda x: FakeBucketObject(fake.url()))
    yield


@pytest.fixture
def context():

    request = HttpRequest()
    request.META["HTTP_ACCEPT"] = "application/json"
    request = Request(request)

    context = {
        "view": None,
        "args": (),
        "kwargs": {},
        "request": request,
    }

    yield context


@pytest.fixture
def set_env(monkeypatch):

    def wrapper(env):
        monkeypatch.setenv("ENV", env)

    yield wrapper


@pytest.fixture
def get_queryset(db, bc: Breathecode):

    def wrapper(n):
        bc.database.create(academy=n)
        academy_cls = bc.database.get_model("admissions.Academy")
        return academy_cls.objects.all()

    yield wrapper


# When: no slug is provided
# Then: the message is returned
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
@pytest.mark.parametrize("env", ["test", "dev", "prod", "qa", "staging", "development", "production", ""])
def test_payment_exception__no_slug(fake, context, set_env, env, extra):
    set_env(env)

    message = fake.sentence()
    extra = extra.copy()

    exc = PaymentException(message, **extra)

    res = exception_handler(exc, context)

    expected = {
        "detail": message,
        "status_code": 402,
    }

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: a slug is provided and the env is test
# Then: the slug is returned
@pytest.mark.parametrize("with_data", [True, False])
@pytest.mark.parametrize("with_queryset", [True, False])
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
def test_payment_exception__test_env__use_the_slug(
    fake, context, set_env, extra, get_kwargs, with_data, get_queryset, with_queryset
):
    set_env("test")

    slug = fake.slug()
    message = fake.sentence()
    extra = extra.copy()

    if with_data:
        data = get_kwargs(5)
        extra["data"] = data

    if with_queryset:
        queryset = get_queryset(5)
        extra["queryset"] = queryset

    exc = PaymentException(message, slug=slug, **extra)
    res = exception_handler(exc, context)

    expected = {
        "detail": slug,
        "status_code": 402,
    }

    if with_data:
        expected["data"] = data

    if with_queryset:
        expected["items"] = [
            {
                "pk": x.id,
                "slug": x.slug,
                "name": x.name,
            }
            for x in queryset
        ]

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: a slug is provided and the env is not test
# Then: the message is returned
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
@pytest.mark.parametrize("env", ["dev", "prod", "qa", "staging", "development", "production", ""])
def test_payment_exception__anything_but_test_env__does_not_use_the_slug(fake, context, set_env, env, extra):
    set_env(env)

    slug = fake.slug()
    message = fake.sentence()

    exc = PaymentException(message, slug=slug, **extra)
    res = exception_handler(exc, context)

    expected = {
        "detail": message,
        "status_code": 402,
    }

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: a slug and silent=True is provided and the env is not test
# Then: the message is returned
@pytest.mark.parametrize("env", ["dev", "prod", "qa", "staging", "development", "production", ""])
def test_payment_exception__anything_but_test_env__silent_code(fake, context, set_env, env):
    set_env(env)

    slug = fake.slug()
    message = fake.sentence()

    exc = PaymentException(message, slug=slug, silent=True)
    res = exception_handler(exc, context)

    assert isinstance(res, Response)
    assert res.data == {
        "detail": message,
        "silent": True,
        "silent_code": slug,
        "status_code": 402,
    }
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: a slug and silent=True is provided and the env is test
# Then: the message is returned
def test_payment_exception__test_env__silent_code(fake, context, set_env):
    set_env("test")

    slug = fake.slug()
    message = fake.sentence()

    exc = PaymentException(message, slug=slug, silent=True)
    res = exception_handler(exc, context)

    assert isinstance(res, Response)
    assert res.data == {
        "detail": slug,
        "silent": True,
        "silent_code": slug,
        "status_code": 402,
    }
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: a slug and silent=True is provided and the env is test with multiple errors
# Then: it returns each error
def test_payment_exception__test_env__multiple_errors(fake, context, set_env, get_kwargs, get_queryset):
    set_env("test")

    slugs = [fake.slug() for _ in range(3)]
    messages = [fake.sentence() for _ in range(5)]
    data = get_kwargs(5)
    queryset = get_queryset(5)

    errors = [
        C(messages[0]),
        C(messages[1], silent=True),
        C(messages[2], slug=slugs[0], silent=True),
        C(messages[3], slug=slugs[1], data=data),
        C(messages[4], slug=slugs[2], queryset=queryset),
    ]

    exc = PaymentException(errors)
    res = exception_handler(exc, context)

    expected = [
        {"detail": messages[0], "status_code": 402},
        {"detail": messages[1], "silent": True, "silent_code": "undefined", "status_code": 402},
        {"detail": slugs[0], "silent": True, "silent_code": slugs[0], "status_code": 402},
        {"data": data, "detail": slugs[1], "status_code": 402},
        {
            "detail": slugs[2],
            "items": [
                {
                    "pk": x.id,
                    "slug": x.slug,
                    "name": x.name,
                }
                for x in queryset
            ],
            "status_code": 402,
        },
    ]

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status.HTTP_402_PAYMENT_REQUIRED


# When: no slug is provided
# Then: the message is returned
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
@pytest.mark.parametrize("env", ["test", "dev", "prod", "qa", "staging", "development", "production", ""])
def test_validation_exception__no_slug(fake, context, set_env, env, extra):
    set_env(env)

    message = fake.sentence()
    extra = extra.copy()
    status_code = get_status_code()

    exc = ValidationException(message, code=status_code, **extra)

    res = exception_handler(exc, context)

    expected = {
        "detail": message,
        "status_code": status_code,
    }

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status_code


# When: a slug is provided and the env is test
# Then: the slug is returned
@pytest.mark.parametrize("with_data", [True, False])
@pytest.mark.parametrize("with_queryset", [True, False])
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
def test_validation_exception__test_env__use_the_slug(
    fake, context, set_env, extra, get_kwargs, with_data, get_queryset, with_queryset
):
    set_env("test")

    slug = fake.slug()
    message = fake.sentence()
    extra = extra.copy()
    status_code = get_status_code()

    if with_data:
        data = get_kwargs(5)
        extra["data"] = data

    if with_queryset:
        queryset = get_queryset(5)
        extra["queryset"] = queryset

    exc = ValidationException(message, slug=slug, code=status_code, **extra)
    res = exception_handler(exc, context)

    expected = {
        "detail": slug,
        "status_code": status_code,
    }

    if with_data:
        expected["data"] = data

    if with_queryset:
        expected["items"] = [
            {
                "pk": x.id,
                "slug": x.slug,
                "name": x.name,
            }
            for x in queryset
        ]

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status_code


# When: a slug is provided and the env is not test
# Then: the message is returned
@pytest.mark.parametrize("extra", [{}, {"silent": False}, {"silent": None}])
@pytest.mark.parametrize("env", ["dev", "prod", "qa", "staging", "development", "production", ""])
def test_validation_exception__anything_but_test_env__does_not_use_the_slug(fake, context, set_env, env, extra):
    set_env(env)

    slug = fake.slug()
    message = fake.sentence()
    status_code = get_status_code()

    exc = ValidationException(message, slug=slug, code=status_code, **extra)
    res = exception_handler(exc, context)

    expected = {
        "detail": message,
        "status_code": status_code,
    }

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status_code


# When: a slug and silent=True is provided and the env is not test
# Then: the message is returned
@pytest.mark.parametrize("env", ["dev", "prod", "qa", "staging", "development", "production", ""])
def test_validation_exception__anything_but_test_env__silent_code(fake, context, set_env, env):
    set_env(env)

    slug = fake.slug()
    message = fake.sentence()
    status_code = get_status_code()

    exc = ValidationException(message, slug=slug, code=status_code, silent=True)
    res = exception_handler(exc, context)

    assert isinstance(res, Response)
    assert res.data == {
        "detail": message,
        "silent": True,
        "silent_code": slug,
        "status_code": status_code,
    }
    assert res.status_code == status_code


# When: a slug and silent=True is provided and the env is test
# Then: the message is returned
def test_validation_exception__test_env__silent_code(fake, context, set_env):
    set_env("test")

    slug = fake.slug()
    message = fake.sentence()
    status_code = get_status_code()

    exc = ValidationException(message, slug=slug, code=status_code, silent=True)
    res = exception_handler(exc, context)

    assert isinstance(res, Response)
    assert res.data == {
        "detail": slug,
        "silent": True,
        "silent_code": slug,
        "status_code": status_code,
    }
    assert res.status_code == status_code


# When: a slug and silent=True is provided and the env is test with multiple errors, any error
# Then: it returns each error
def test_validation_exception__test_env__any_status_code__multiple_errors(
    fake, context, set_env, get_kwargs, get_queryset
):
    set_env("test")

    slugs = [fake.slug() for _ in range(3)]
    messages = [fake.sentence() for _ in range(5)]
    status_codes = [get_status_code() for _ in range(4)]
    data = get_kwargs(5)
    queryset = get_queryset(5)

    status_code = get_status_code()

    errors = [
        C(messages[0]),
        C(messages[1], code=status_codes[0], silent=True),
        C(messages[2], slug=slugs[0], code=status_codes[1], silent=True),
        C(messages[3], slug=slugs[1], code=status_codes[2], data=data),
        C(messages[4], slug=slugs[2], code=status_codes[3], queryset=queryset),
    ]

    exc = ValidationException(errors, code=status_code)
    res = exception_handler(exc, context)

    expected = [
        {
            "detail": messages[0],
            "status_code": status_code,
        },
        {
            "detail": messages[1],
            "silent": True,
            "silent_code": "undefined",
            "status_code": status_code,
        },
        {
            "detail": slugs[0],
            "silent": True,
            "silent_code": slugs[0],
            "status_code": status_code,
        },
        {
            "data": data,
            "detail": slugs[1],
            "status_code": status_code,
        },
        {
            "detail": slugs[2],
            "items": [
                {
                    "pk": x.id,
                    "slug": x.slug,
                    "name": x.name,
                }
                for x in queryset
            ],
            "status_code": status_code,
        },
    ]

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == status_code


# When: a slug and silent=True is provided and the env is test with multiple errors, 207
# Then: it returns each error
def test_validation_exception__test_env__207__multiple_errors(fake, context, set_env, get_kwargs, get_queryset):
    set_env("test")

    slugs = [fake.slug() for _ in range(3)]
    messages = [fake.sentence() for _ in range(5)]
    status_codes = [get_status_code() for _ in range(4)]
    data = get_kwargs(5)
    queryset = get_queryset(5)

    errors = [
        C(messages[0]),
        C(messages[1], code=status_codes[0], silent=True),
        C(messages[2], slug=slugs[0], code=status_codes[1], silent=True),
        C(messages[3], slug=slugs[1], code=status_codes[2], data=data),
        C(messages[4], slug=slugs[2], code=status_codes[3], queryset=queryset),
    ]

    exc = ValidationException(errors, code=207)
    res = exception_handler(exc, context)

    expected = [
        {
            "detail": messages[0],
            "status_code": 400,
        },
        {
            "detail": messages[1],
            "silent": True,
            "silent_code": "undefined",
            "status_code": status_codes[0],
        },
        {
            "detail": slugs[0],
            "silent": True,
            "silent_code": slugs[0],
            "status_code": status_codes[1],
        },
        {
            "data": data,
            "detail": slugs[1],
            "status_code": status_codes[2],
        },
        {
            "detail": slugs[2],
            "items": [
                {
                    "pk": x.id,
                    "slug": x.slug,
                    "name": x.name,
                }
                for x in queryset
            ],
            "status_code": status_codes[3],
        },
    ]

    assert isinstance(res, Response)
    assert res.data == expected
    assert res.status_code == 207
