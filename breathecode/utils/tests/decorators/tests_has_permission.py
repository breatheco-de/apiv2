import json

import pytest
from adrf.decorators import APIView, api_view
from asgiref.sync import sync_to_async
from django.http.response import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

import breathecode.utils.decorators as decorators
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from capyc.rest_framework import pytest as capy

PERMISSION = 'can_kill_kenny'
UTC_NOW = timezone.now()


def build_view_function(method, data, decorator_args=(), decorator_kwargs={}, with_id=False, is_async=False):

    if is_async:

        @api_view([method])
        @permission_classes([AllowAny])
        @decorators.has_permission(*decorator_args, **decorator_kwargs)
        async def view_function(request, *args, **kwargs):
            if with_id:
                assert kwargs['id'] == 1

            else:
                assert 'id' not in kwargs

            return Response(data)

        return view_function

    @api_view([method])
    @permission_classes([AllowAny])
    @decorators.has_permission(*decorator_args, **decorator_kwargs)
    def view_function(request, *args, **kwargs):
        if with_id:
            assert kwargs['id'] == 1

        else:
            assert 'id' not in kwargs

        return Response(data)

    return view_function


def build_view_class(method, data, decorator_args=(), decorator_kwargs={}, with_id=False, is_async=False):

    class BaseView(APIView):
        """
        List all snippets, or create a new snippet.
        """
        permission_classes = [AllowAny]

    BaseView.__test__ = False

    @decorators.has_permission(*decorator_args, **decorator_kwargs)
    def sync_method(self, request, *args, **kwargs):
        if with_id:
            assert kwargs['id'] == 1

        else:
            assert 'id' not in kwargs

        return Response(data)

    @decorators.has_permission(*decorator_args, **decorator_kwargs)
    async def async_method(self, request, *args, **kwargs):
        if with_id:
            assert kwargs['id'] == 1

        else:
            assert 'id' not in kwargs

        return Response(data)

    setattr(BaseView, method.lower(), async_method if is_async else sync_method)

    return BaseView


def build_params():
    methods = ['get', 'post', 'put', 'delete']
    class_baseds = [True, False]
    with_ids = [True, False]
    is_asyncs = [True, False]

    for method in methods:
        for class_based in class_baseds:
            for with_id in with_ids:
                if method not in ['get', 'post'] and with_id is False:
                    continue

                if method == 'post' and with_id is True:
                    continue

                for is_async in is_asyncs:
                    args = (method, class_based, with_id, is_async)
                    yield args, 'method_{}__class_based_{}__with_id_{}__is_async_{}'.format(*args)


@pytest.fixture(params=[param for param, _ in build_params()], ids=[id for _, id in build_params()])
def make_view(request, fake):
    method, class_based, with_id, is_async = request.param
    res = {
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
        fake.slug(): fake.slug(),
    }

    def wrapper(user=None, decorator_params={}, url_params={}):
        nonlocal method

        if with_id:
            url_params['id'] = 1

        if class_based:
            view = build_view_class(method.upper(),
                                    res,
                                    decorator_args=(PERMISSION, ),
                                    decorator_kwargs=decorator_params,
                                    with_id=with_id,
                                    is_async=is_async)
            view = view.as_view()

        else:
            view = build_view_function(method.upper(),
                                       res,
                                       decorator_args=(PERMISSION, ),
                                       decorator_kwargs=decorator_params,
                                       with_id=with_id,
                                       is_async=is_async)

        factory = APIRequestFactory()
        url = '/they-killed-kenny'
        if with_id:
            url += f'/{url_params["id"]}'

        handler = getattr(factory, method.lower())

        request = handler(url)

        if user:
            force_authenticate(request, user=user)

        def sync_get_response():
            x = view(request, **url_params)
            if isinstance(x, JsonResponse):
                return x, res

            return x.render(), res

        async def async_get_response():
            x = await view(request, **url_params)

            if isinstance(x, JsonResponse):
                return x, res

            return x.render(), res

        if is_async:
            return async_get_response

        return sync_to_async(sync_get_response)

    if is_async:
        return sync_to_async(wrapper)

    return sync_to_async(wrapper)


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test__anonymous_user(database: capy.Database, make_view):
    view = await make_view(user=None, decorator_params={}, url_params={})

    response, _ = await view()
    expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

    assert json.loads(response.content.decode('utf-8')) == expected
    assert response.status_code, status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test__with_user(database: capy.Database, make_view):
    model = await database.acreate(user=1)

    view = await make_view(user=model.user, decorator_params={}, url_params={})

    response, _ = await view()
    expected = {'detail': 'without-permission', 'status_code': 403}

    assert json.loads(response.content.decode('utf-8')) == expected
    assert response.status_code, status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test__with_user__with_permission__dont_match(database: capy.Database, make_view):
    model = await database.acreate(user=1, permission=1)

    view = await make_view(user=model.user, decorator_params={}, url_params={})

    response, _ = await view()
    expected = {'detail': 'without-permission', 'status_code': 403}

    assert json.loads(response.content.decode('utf-8')) == expected
    assert response.status_code, status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test__with_user__with_permission(bc: Breathecode, make_view):
    permission = {'codename': PERMISSION}
    model = await bc.database.acreate(user=1, permission=permission)

    view = await make_view(user=model.user, decorator_params={}, url_params={})

    response, expected = await view()

    assert json.loads(response.content.decode('utf-8')) == expected
    assert response.status_code, status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test__with_user__with_group_related_to_permission(bc: Breathecode, make_view):
    user = {'user_permissions': []}
    permissions = [{}, {'codename': PERMISSION}]
    group = {'permission_pk': 2}
    model = await bc.database.acreate(user=user, permission=permissions, group=group)

    view = await make_view(user=model.user, decorator_params={}, url_params={})

    response, expected = await view()

    assert json.loads(response.content.decode('utf-8')) == expected
    assert response.status_code, status.HTTP_200_OK
