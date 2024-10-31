from datetime import datetime
from typing import Any, Callable, Optional, Tuple, Unpack
from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from adrf.requests import AsyncRequest
from adrf.test import AsyncAPIRequestFactory
from capyc.core.managers import feature
from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet, Sum
from django.urls.base import reverse_lazy
from rest_framework.test import APIRequestFactory

from breathecode.payments.models import Consumable
from breathecode.payments.utils import ConsumableType, consumable, service_item
from breathecode.utils.decorators.consume import ServiceContext


@pytest.fixture(autouse=True)
def setup(db: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.events.models.LiveClass._get_hash", lambda self: "abc")

    yield


def build_context(
    request: WSGIRequest | AsyncRequest,
    service: str,
    utc_now: datetime,
    consumables: QuerySet[Consumable] = Consumable.objects.none(),
    flags: Optional[dict[str, Any]] = None,
    **opts: Unpack[ServiceContext],
) -> ServiceContext:

    if flags is None:
        flags = {}

    return {
        "utc_now": utc_now,
        "consumer": None,
        "service": service,
        "request": request,
        "consumables": consumables,
        "lifetime": None,
        "price": 1,
        "is_consumption_session": False,
        "flags": flags,
        **opts,
    }


PatchBypassConsumption = Callable[[Tuple[ConsumableType, ...]], list[ConsumableType]]


@pytest.fixture
def patch_bypass_consumption(monkeypatch: pytest.MonkeyPatch):
    def wrapper(*args: ConsumableType) -> list[ConsumableType]:
        monkeypatch.setattr("breathecode.payments.data.get_virtual_consumables", MagicMock(return_value=[*args]))

    yield wrapper


PatchFlag = Callable[[str], None]


@pytest.fixture(autouse=True)
def patch_flag(monkeypatch: pytest.MonkeyPatch):
    def wrapper(v: str) -> None:
        monkeypatch.setattr("breathecode.payments.flags.flags", {"BYPASS_CONSUMPTION": v})

    wrapper("0")

    yield wrapper


def test_flag_true(database: capy.Database, patch_flag: PatchFlag):
    patch_flag("1")
    model = database.create(user=1)

    factory = APIRequestFactory()
    url = "/my/url"

    request = factory.get(url)
    request.user = model.user

    kwargs = {}
    service_context = ServiceContext(
        # consumer=False,
        service="event_join",
        request=request,
    )

    context = feature.context(context=service_context, kwargs=kwargs)
    res = feature.is_enabled("payments.bypass_consumption", context=context)
    assert res is True


class TestEventJoin:
    @pytest.mark.parametrize(
        "models",
        [
            {
                "event_type": {"description": "abc"},
                "event_type_set": {"event_types": []},
                "service_item": 1,
            },
            {
                "event": 1,
                "event_type": {"description": "abc"},
                "event_type_set": {"event_types": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
        ],
    )
    def test_false(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, event_type_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"event_id": 1}
        service_context = ServiceContext(
            # consumer=False,
            service="event_join",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is False

    @pytest.mark.parametrize(
        "models",
        [
            {
                "event": 1,
                "event_type": {"description": "abc"},
                "event_type_set": {"event_types": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_true(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, event_type_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"event_id": 1}
        service_context = ServiceContext(
            # consumer=False,
            service="event_join",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is True


class TestLiveClassJoin:
    @pytest.mark.parametrize(
        "models",
        [
            {
                "cohort": {"available_as_saas": True},
                "cohort_set": {"cohorts": [1]},
                "live_class": {"hash": "abc"},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "live_class": {"hash": "abc"},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": []},
                "live_class": {"hash": "abc"},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "live_class": {"hash": "abcd"},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
        ],
    )
    def test_false(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"event_id": 1}
        service_context = ServiceContext(
            # consumer=False,
            service="live_class_join",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is False

    @pytest.mark.parametrize(
        "models",
        [
            {
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "live_class": {"hash": "abc"},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "live_class": {"hash": "abc"},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_true(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"hash": "abc"}
        service_context = ServiceContext(
            # consumer=False,
            service="live_class_join",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is True


class TestJoinMentorship:
    @pytest.mark.parametrize(
        "models",
        [
            {
                "mentorship_service": {"slug": "abc"},
                "mentorship_service_set": {"mentorship_services": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "mentorship_service": {"slug": "abcd"},
                "mentorship_service_set": {"mentorship_services": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_false(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, mentorship_service_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"service_slug": "abc"}
        service_context = ServiceContext(
            # consumer=False,
            service="join_mentorship",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is False

    @pytest.mark.parametrize(
        "models",
        [
            {
                "mentorship_service": {"slug": "abc"},
                "mentorship_service_set": {"mentorship_services": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_true(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, mentorship_service_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"service_slug": "abc"}
        service_context = ServiceContext(
            # consumer=False,
            service="join_mentorship",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is True


class TestAddCodeReview:
    @pytest.mark.parametrize(
        "models",
        [
            {
                "task": 1,
                "cohort": {"available_as_saas": True},
                "cohort_set": {"cohorts": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "task": 1,
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "task": 1,
                "cohort": {"available_as_saas": True},
                "cohort_set": {"cohorts": []},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
        ],
    )
    def test_false(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"task_id": 1}
        service_context = ServiceContext(
            # consumer=False,
            service="add_code_review",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is False

    @pytest.mark.parametrize(
        "models",
        [
            {
                "task": 1,
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "task": 1,
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_true(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"task_id": 1}
        service_context = ServiceContext(
            # consumer=False,
            service="add_code_review",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is True


class TestReadLesson:
    @pytest.mark.parametrize(
        "models",
        [
            {
                "asset": {"slug": "abc"},
                "asset_category": 1,
                "cohort": {"available_as_saas": True},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abc"}},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "asset": {"slug": "abc"},
                "asset_category": 1,
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abc"}},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "asset": {"slug": "abcd"},
                "asset_category": 1,
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abc"}},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "asset": {"slug": "abc"},
                "asset_category": 1,
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abcd"}},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
        ],
    )
    def test_false(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"asset_slug": "abc"}
        service_context = ServiceContext(
            # consumer=False,
            service="read_lesson",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is False

    @pytest.mark.parametrize(
        "models",
        [
            {
                "asset": {"slug": "abc"},
                "asset_category": 1,
                "cohort": {"available_as_saas": False},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abc"}},
                "service_item": 1,
                "academy": {"available_as_saas": True},
            },
            {
                "asset": {"slug": "abc"},
                "asset_category": 1,
                "cohort": {"available_as_saas": None},
                "cohort_set": {"cohorts": [1]},
                "cohort_user": 1,
                "syllabus_version": {"json": {"bla": "abc"}},
                "service_item": 1,
                "academy": {"available_as_saas": False},
            },
        ],
    )
    def test_true(
        self, database: capy.Database, patch_bypass_consumption: PatchBypassConsumption, models: dict[str, int]
    ):
        model = database.create(city=1, country=1, user=1, **models)
        patch_bypass_consumption(consumable(service_item=1, cohort_set=1))

        factory = APIRequestFactory()
        url = "/my/url"

        request = factory.get(url)
        request.user = model.user

        kwargs = {"asset_slug": "abc"}
        service_context = ServiceContext(
            # consumer=False,
            service="read_lesson",
            request=request,
        )

        context = feature.context(context=service_context, kwargs=kwargs)
        res = feature.is_enabled("payments.bypass_consumption", context=context)
        assert res is True
