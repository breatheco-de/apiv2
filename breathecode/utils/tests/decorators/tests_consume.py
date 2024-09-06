import json
import random
from datetime import timedelta
from unittest.mock import MagicMock, call

import capyc.pytest as capy
import pytest
from adrf.decorators import APIView, api_view
from asgiref.sync import sync_to_async
from django.http.response import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

import breathecode.utils.decorators as decorators
from breathecode.payments import models
from breathecode.payments import signals as payments_signals
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.utils.decorators import ServiceContext

SERVICE = random.choice([value for value, _ in models.Service.Consumer.choices])
UTC_NOW = timezone.now()


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    monkeypatch.setattr("breathecode.payments.signals.consume_service.send_robust", MagicMock(return_value=None))
    monkeypatch.setattr(
        "breathecode.payments.models.ConsumptionSession.build_session",
        MagicMock(wraps=models.ConsumptionSession.build_session),
    )

    CONSUMER_MOCK.call_args_list = []
    CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []


def consumer(context: ServiceContext, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    # remember the objects are passed by reference, so you need to clone them to avoid modify the object
    # receive by the mock causing side effects
    args = (*args, SERVICE)
    kwargs = {
        **kwargs,
        "permission": SERVICE,
    }
    context = {
        **context,
        "consumables": context["consumables"].exclude(service_item__service__groups__name="secret"),
    }

    return (context, args, kwargs)


CONSUMER_MOCK = MagicMock(wraps=consumer)

time_of_life = timedelta(days=random.randint(1, 100))


def consumer_with_time_of_life(context: ServiceContext, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    # remember the objects are passed by reference, so you need to clone them to avoid modify the object
    # receive by the mock causing side effects
    args = (*args, SERVICE)
    kwargs = {
        **kwargs,
        "permission": SERVICE,
    }
    context = {
        **context,
        "consumables": context["consumables"].exclude(service_item__service__groups__name="secret"),
        "time_of_life": time_of_life,
    }

    return (context, args, kwargs)


CONSUMER_WITH_TIME_OF_LIFE_MOCK = MagicMock(wraps=consumer)


def build_view_function(method, data, decorator_args=(), decorator_kwargs={}, with_id=False, is_async=False):

    if is_async:

        @api_view([method])
        @permission_classes([AllowAny])
        @decorators.consume(*decorator_args, **decorator_kwargs)
        async def view_function(request, *args, **kwargs):
            if with_id:
                assert kwargs["id"] == 1

            else:
                assert "id" not in kwargs

            return Response(data)

        return view_function

    @api_view([method])
    @permission_classes([AllowAny])
    @decorators.consume(*decorator_args, **decorator_kwargs)
    def view_function(request, *args, **kwargs):
        if with_id:
            assert kwargs["id"] == 1

        else:
            assert "id" not in kwargs

        return Response(data)

    return view_function


def build_view_class(method, data, decorator_args=(), decorator_kwargs={}, with_id=False, is_async=False):

    class BaseView(APIView):
        """
        List all snippets, or create a new snippet.
        """

        permission_classes = [AllowAny]

    BaseView.__test__ = False

    @decorators.consume(*decorator_args, **decorator_kwargs)
    def sync_method(self, request, *args, **kwargs):
        if with_id:
            assert kwargs["id"] == 1

        else:
            assert "id" not in kwargs

        return Response(data)

    @decorators.consume(*decorator_args, **decorator_kwargs)
    async def async_method(self, request, *args, **kwargs):
        if with_id:
            assert kwargs["id"] == 1

        else:
            assert "id" not in kwargs

        return Response(data)

    setattr(BaseView, method.lower(), async_method if is_async else sync_method)

    return BaseView


def build_params():
    methods = ["get", "post", "put", "delete"]
    class_baseds = [True, False]
    with_ids = [True, False]
    is_asyncs = [True, False]

    for method in methods:
        for class_based in class_baseds:
            for with_id in with_ids:
                if method not in ["get", "post"] and with_id is False:
                    continue

                if method == "post" and with_id is True:
                    continue

                for is_async in is_asyncs:
                    args = (method, class_based, with_id, is_async)
                    yield args, "method_{}__class_based_{}__with_id_{}__is_async_{}".format(*args)


def make_view(request, fake, decorator_params={}):
    method, class_based, with_id, is_async = request.param
    res = {
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
    }

    decorator_params_in_fixture = decorator_params
    extra = {}
    if with_id:
        extra["id"] = 1

    @sync_to_async
    def wrapper(user=None, decorator_params={}, url_params={}):
        nonlocal method, decorator_params_in_fixture

        if decorator_params_in_fixture:
            decorator_params = decorator_params_in_fixture

        if with_id:
            url_params = {**url_params, **extra}

        if class_based:
            view = build_view_class(
                method.upper(),
                res,
                decorator_args=(SERVICE,),
                decorator_kwargs=decorator_params,
                with_id=with_id,
                is_async=is_async,
            )
            view = view.as_view()

        else:
            view = build_view_function(
                method.upper(),
                res,
                decorator_args=(SERVICE,),
                decorator_kwargs=decorator_params,
                with_id=with_id,
                is_async=is_async,
            )

        factory = APIRequestFactory()
        url = "/they-killed-kenny"
        if with_id:
            url += f'/{url_params["id"]}'

        handler = getattr(factory, method.lower())

        request = handler(url)

        if user:
            force_authenticate(request, user=user)

        def sync_get_response():
            x = view(request, **url_params)
            if isinstance(x, JsonResponse):
                return x, url_params

            return x.render(), url_params

        async def async_get_response():
            x = await view(request, **url_params)

            if isinstance(x, JsonResponse):
                return x, url_params

            return x.render(), url_params

        if is_async:
            return async_get_response

        return sync_to_async(sync_get_response)

    async def unpack(user=None, decorator_params={}, url_params={}):

        if with_id:
            url_params = {**url_params, **extra}

        return (
            await wrapper(user=user, decorator_params=decorator_params, url_params=url_params),
            res,
            class_based,
            url_params,
        )

    return unpack


@pytest.fixture(params=[param for param, _ in build_params()], ids=[id for _, id in build_params()])
def make_view_all_cases(request, fake):
    return make_view(request, fake)


@pytest.fixture(params=[param for param, _ in build_params()], ids=[id for _, id in build_params()])
def make_view_consumer_cases(request, fake):
    return make_view(request, fake, decorator_params={"consumer": CONSUMER_MOCK})


@pytest.fixture(params=[param for param, _ in build_params()], ids=[id for _, id in build_params()])
def make_view_lifetime_cases(request, fake):
    return make_view(request, fake, decorator_params={"consumer": CONSUMER_WITH_TIME_OF_LIFE_MOCK})


class TestNoConsumer:

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_anonymous_user(self, database: capy.Database, make_view_all_cases):
        view, _, _, _ = await make_view_all_cases(user=None, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "anonymous-user-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user(self, database: capy.Database, make_view_all_cases):
        model = await database.acreate(user=1)
        view, _, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_permission__dont_match(self, database: capy.Database, make_view_all_cases):
        model = await database.acreate(user=1, permission=1)
        view, _, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_group_related_to_permission__without_consumable(
        self, bc: Breathecode, make_view_all_cases
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        model = await bc.database.acreate(user=user, service=services, service_item={"service_id": 2})
        view, _, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_group_related_to_permission__consumable__how_many_minus_1(
        self, bc: Breathecode, make_view_all_cases
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": -1}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_group_related_to_permission__consumable__how_many_0(
        self, bc: Breathecode, make_view_all_cases
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": 0}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, _, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_group_related_to_permission__consumable__how_many_gte_1(
        self, bc: Breathecode, make_view_all_cases
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": random.randint(1, 100)}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test_with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(
        self, bc: Breathecode, make_view_all_cases
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]
        group = {"permission_id": 2, "name": "secret"}
        consumable = {"how_many": 1}
        model = await bc.database.acreate(
            user=user, service=services, group=group, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, _, _ = await make_view_all_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()


class TestConsumer:

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__anonymous_user(self, bc: Breathecode, make_view_consumer_cases):
        view, _, _, _ = await make_view_consumer_cases(user=None, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "anonymous-user-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user(self, bc: Breathecode, make_view_consumer_cases):
        model = await bc.database.acreate(user=1)
        view, _, _, _ = await make_view_consumer_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_permission__dont_match(
        self, bc: Breathecode, make_view_consumer_cases
    ):
        model = await bc.database.acreate(user=1, permission=1)
        view, _, _, _ = await make_view_consumer_cases(user=model.user, decorator_params={}, url_params={})

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_group_related_to_permission__without_consumable(
        self, bc: Breathecode, make_view_consumer_cases, partial_equality
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        model = await bc.database.acreate(user=user, service=services, service_item={"service_id": 2})
        view, _, based_class, _ = await make_view_consumer_cases(user=model.user, decorator_params={}, url_params={})

        response, params = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_minus_1(
        self, bc: Breathecode, make_view_consumer_cases, partial_equality
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": -1}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, based_class, params = await make_view_consumer_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_0(
        self, bc: Breathecode, make_view_consumer_cases, partial_equality
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": 0}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, _, based_class, params = await make_view_consumer_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_gte_1(
        self, bc: Breathecode, make_view_consumer_cases, partial_equality
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": random.randint(1, 100)}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, based_class, params = await make_view_consumer_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(
        self, bc: Breathecode, make_view_consumer_cases, partial_equality
    ):
        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]
        group = {"permission_id": 2, "name": "secret"}
        consumable = {"how_many": 1}
        model = await bc.database.acreate(
            user=user, service=services, group=group, service_item={"service_id": 2}, consumable=consumable
        )

        view, _, based_class, params = await make_view_consumer_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, _ = await view()
        expected = {"detail": "with-consumer-not-enough-consumables", "status_code": 402}

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__function__get__with_user__without_consumption_session(
        self, bc: Breathecode, make_view_lifetime_cases, partial_equality
    ):

        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": 1}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable
        )

        view, expected, based_class, _ = await make_view_lifetime_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, params = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_WITH_TIME_OF_LIFE_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params

        assert await bc.database.alist_of("payments.ConsumptionSession") == []
        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()


class TestConsumptionSession:

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__with_user__consumption_session__does_not_match(
        self, bc: Breathecode, make_view_lifetime_cases, partial_equality
    ):

        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": 1}
        model = await bc.database.acreate(
            user=user, service=services, service_item={"service_id": 2}, consumable=consumable, consumption_session=1
        )

        view, expected, based_class, params = await make_view_lifetime_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        Consumable = bc.database.get_model("payments.Consumable")
        consumables = Consumable.objects.filter()
        assert len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list) == 1

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        assert isinstance(context["request"], Request)
        partial_equality(
            context,
            {
                "utc_now": UTC_NOW,
                "consumer": CONSUMER_WITH_TIME_OF_LIFE_MOCK,
                "permission": SERVICE,
                "consumables": consumables,
            },
        )

        if based_class:
            assert len(args) == 2
            assert isinstance(args[1], Request)

        else:
            assert len(args) == 1
            assert isinstance(args[0], Request)

        assert kwargs == params
        assert await bc.database.alist_of("payments.ConsumptionSession") == [
            bc.format.to_dict(model.consumption_session),
        ]

        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == [
                call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
            ]

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(
        self, bc: Breathecode, make_view_lifetime_cases
    ):

        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        n = random.randint(1, 4)
        consumable = {"how_many": n}
        consumption_session = {
            "eta": UTC_NOW + time_of_life,
            "how_many": n,
            "request": {"args": [], "kwargs": {}, "headers": {"academy": None}, "user": 1},
        }
        model = await bc.database.acreate(
            user=user,
            service=services,
            service_item={"service_id": 2},
            consumable=consumable,
            consumption_session=consumption_session,
        )

        view, expected, based_class, params = await make_view_lifetime_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        model.consumption_session.request["kwargs"] = params
        await model.consumption_session.asave()

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        assert len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list) == 1

        assert await bc.database.alist_of("payments.ConsumptionSession") == [
            bc.format.to_dict(model.consumption_session),
        ]

        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    async def test__with_user__consumption_session__match(self, bc: Breathecode, make_view_lifetime_cases):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {"user_permissions": []}
        services = [{}, {"consumer": SERVICE.upper()}]

        consumable = {"how_many": 1}
        consumption_session = {
            "eta": UTC_NOW + time_of_life,
            "request": {"args": [], "kwargs": {}, "headers": {"academy": None}, "user": 1},
        }
        model = await bc.database.acreate(
            user=user,
            service=services,
            service_item={"service_id": 2},
            consumable=consumable,
            consumption_session=consumption_session,
        )

        view, expected, based_class, params = await make_view_lifetime_cases(
            user=model.user, decorator_params={}, url_params={}
        )

        model.consumption_session.request["kwargs"] = params

        await model.consumption_session.asave()

        response, _ = await view()

        assert json.loads(response.content.decode("utf-8")) == expected
        assert response.status_code == status.HTTP_200_OK

        assert len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list) == 1

        assert await bc.database.alist_of("payments.ConsumptionSession") == [
            bc.format.to_dict(model.consumption_session),
        ]

        assert models.ConsumptionSession.build_session.call_args_list == []

        @sync_to_async
        def check_consume_service():
            assert payments_signals.consume_service.send_robust.call_args_list == []

        await check_consume_service()
