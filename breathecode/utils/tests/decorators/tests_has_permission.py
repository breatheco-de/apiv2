import json
import random
from datetime import timedelta
from functools import wraps
from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

import breathecode.utils.decorators as decorators
from breathecode.payments import models
from breathecode.payments import signals as payments_signals
from breathecode.utils.decorators import PermissionContextType

from ..mixins import UtilsTestCase

PERMISSION = 'can_kill_kenny'
GET_RESPONSE = {'a': 1}
GET_ID_RESPONSE = {'a': 2}
POST_RESPONSE = {'a': 3}
PUT_ID_RESPONSE = {'a': 4}
DELETE_ID_RESPONSE = {'a': 5}
UTC_NOW = timezone.now()


def consumer(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    # remember the objects are passed by reference, so you need to clone them to avoid modify the object
    # receive by the mock causing side effects
    args = (*args, PERMISSION)
    kwargs = {
        **kwargs,
        'permission': PERMISSION,
    }
    context = {
        **context,
        'consumables': context['consumables'].exclude(service_item__service__groups__name='secret'),
    }

    return (context, args, kwargs)


CONSUMER_MOCK = MagicMock(wraps=consumer)

time_of_life = timedelta(days=random.randint(1, 100))


def consumer_with_time_of_life(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    # remember the objects are passed by reference, so you need to clone them to avoid modify the object
    # receive by the mock causing side effects
    args = (*args, PERMISSION)
    kwargs = {
        **kwargs,
        'permission': PERMISSION,
    }
    context = {
        **context,
        'consumables': context['consumables'].exclude(service_item__service__groups__name='secret'),
        'time_of_life': time_of_life,
    }

    return (context, args, kwargs)


CONSUMER_WITH_TIME_OF_LIFE_MOCK = MagicMock(wraps=consumer)


def build_view_function(methods,
                        data,
                        decorator,
                        decorator_args=(),
                        decorator_kwargs={},
                        with_permission=False,
                        with_id=False):

    @api_view(methods)
    @permission_classes([AllowAny])
    @decorator(*decorator_args, **decorator_kwargs)
    def view_function(request, *args, **kwargs):
        if with_permission:
            assert kwargs['permission'] == PERMISSION
            assert args[0] == PERMISSION

        if with_id:
            assert kwargs['id'] == 1

        return Response(data)

    return view_function


get = build_view_function(['GET'], GET_RESPONSE, decorators.has_permission, decorator_args=(PERMISSION, ))
get_consumer = build_view_function(['GET'],
                                   GET_RESPONSE,
                                   decorators.has_permission,
                                   decorator_args=(PERMISSION, ),
                                   decorator_kwargs={'consumer': True})

get_consumer_callback = build_view_function(['GET'],
                                            GET_RESPONSE,
                                            decorators.has_permission,
                                            decorator_args=(PERMISSION, ),
                                            decorator_kwargs={'consumer': CONSUMER_MOCK},
                                            with_permission=True)

get_consumer_callback_with_time_of_life = build_view_function(
    ['GET'],
    GET_RESPONSE,
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK},
    with_permission=False)

get_id = build_view_function(['GET'],
                             GET_ID_RESPONSE,
                             decorators.has_permission,
                             decorator_args=(PERMISSION, ),
                             with_id=True)

get_id_consumer = build_view_function(['GET'],
                                      GET_ID_RESPONSE,
                                      decorators.has_permission,
                                      decorator_args=(PERMISSION, ),
                                      decorator_kwargs={'consumer': True},
                                      with_id=True)

get_id_consumer_callback = build_view_function(['GET'],
                                               GET_ID_RESPONSE,
                                               decorators.has_permission,
                                               decorator_args=(PERMISSION, ),
                                               decorator_kwargs={'consumer': CONSUMER_MOCK},
                                               with_id=True,
                                               with_permission=True)

get_id_consumer_callback_with_time_of_life = build_view_function(
    ['GET'],
    GET_ID_RESPONSE,
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK},
    with_id=True,
    with_permission=False)

post = build_view_function(['POST'], POST_RESPONSE, decorators.has_permission, decorator_args=(PERMISSION, ))
post_consumer = build_view_function(['POST'],
                                    POST_RESPONSE,
                                    decorators.has_permission,
                                    decorator_args=(PERMISSION, ),
                                    decorator_kwargs={'consumer': True})

post_consumer_callback = build_view_function(['POST'],
                                             POST_RESPONSE,
                                             decorators.has_permission,
                                             decorator_args=(PERMISSION, ),
                                             decorator_kwargs={'consumer': CONSUMER_MOCK},
                                             with_permission=True)

post_consumer_callback_with_time_of_life = build_view_function(
    ['POST'],
    POST_RESPONSE,
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK},
    with_permission=False)

put_id = build_view_function(['PUT'],
                             PUT_ID_RESPONSE,
                             decorators.has_permission,
                             decorator_args=(PERMISSION, ),
                             with_id=True)

put_id_consumer = build_view_function(['PUT'],
                                      PUT_ID_RESPONSE,
                                      decorators.has_permission,
                                      decorator_args=(PERMISSION, ),
                                      decorator_kwargs={'consumer': True},
                                      with_id=True)

put_id_consumer_callback = build_view_function(['PUT'],
                                               PUT_ID_RESPONSE,
                                               decorators.has_permission,
                                               decorator_args=(PERMISSION, ),
                                               decorator_kwargs={'consumer': CONSUMER_MOCK},
                                               with_id=True,
                                               with_permission=True)

put_id_consumer_callback_with_time_of_life = build_view_function(
    ['PUT'],
    PUT_ID_RESPONSE,
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK},
    with_id=True,
    with_permission=False)

delete_id = build_view_function(['DELETE'],
                                DELETE_ID_RESPONSE,
                                decorators.has_permission,
                                decorator_args=(PERMISSION, ),
                                with_id=True)

delete_id_consumer = build_view_function(['DELETE'],
                                         DELETE_ID_RESPONSE,
                                         decorators.has_permission,
                                         decorator_args=(PERMISSION, ),
                                         decorator_kwargs={'consumer': True},
                                         with_id=True)

delete_id_consumer_callback = build_view_function(['DELETE'],
                                                  DELETE_ID_RESPONSE,
                                                  decorators.has_permission,
                                                  decorator_args=(PERMISSION, ),
                                                  decorator_kwargs={'consumer': CONSUMER_MOCK},
                                                  with_id=True,
                                                  with_permission=True)

delete_id_consumer_callback_with_time_of_life = build_view_function(
    ['DELETE'],
    DELETE_ID_RESPONSE,
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK},
    with_id=True,
    with_permission=False)


def build_view_class(decorator, decorator_args=(), decorator_kwargs={}, with_permission=False):

    class CustomView(APIView):
        """
        List all snippets, or create a new snippet.
        """
        permission_classes = [AllowAny]

        @staticmethod
        def decorate(func):

            def wrapper(request, *args, **kwargs):
                if with_permission:
                    assert kwargs.get('permission') == PERMISSION
                    assert args[0] == PERMISSION

                return func(request, *args, **kwargs)

            return decorator(*decorator_args, **decorator_kwargs)(wrapper)

        def get(self, request, *args, **kwargs):
            if 'id' in kwargs:
                assert kwargs['id'] == 1
                return Response(GET_ID_RESPONSE)
            return Response(GET_RESPONSE)

        get = decorate(get)

        def post(self, request, *args, **kwargs):
            return Response(POST_RESPONSE)

        post = decorate(post)

        def put(self, request, *args, **kwargs):
            if 'id' not in kwargs:
                assert 0
            assert kwargs['id'] == 1
            return Response(PUT_ID_RESPONSE)

        put = decorate(put)

        def delete(self, request, *args, **kwargs):
            if 'id' not in kwargs:
                assert 0
            assert kwargs['id'] == 1
            return Response(DELETE_ID_RESPONSE)

        delete = decorate(delete)

    CustomView.__test__ = False

    return CustomView


TestView = build_view_class(decorators.has_permission, decorator_args=(PERMISSION, ))
TestViewConsumer = build_view_class(decorators.has_permission,
                                    decorator_args=(PERMISSION, ),
                                    decorator_kwargs={'consumer': True})

TestViewConsumerCallback = build_view_class(decorators.has_permission,
                                            decorator_args=(PERMISSION, ),
                                            decorator_kwargs={'consumer': CONSUMER_MOCK})

TestViewConsumerCallbackWithTimeOfLife = build_view_class(
    decorators.has_permission,
    decorator_args=(PERMISSION, ),
    decorator_kwargs={'consumer': CONSUMER_WITH_TIME_OF_LIFE_MOCK})


class FunctionBasedViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

    def tearDown(self) -> None:
        super().tearDown()
        CONSUMER_MOCK.call_args_list = []
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

    """
    🔽🔽🔽 Function get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')

        view = post

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])


class ConsumerFunctionBasedViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []

    """
    🔽🔽🔽 Function get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_consumer

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 Function get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 Function post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')

        view = post_consumer

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 Function put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 Function delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])


class ConsumerFunctionCallbackBasedViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []

    """
    🔽🔽🔽 Function get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__get_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__post__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post_consumer_callback_with_time_of_life

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__put_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 Function delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__without_consumable(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__consumable__how_many_gte_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': random.randint(1, 100)}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__with_group_related_to_permission__group_was_blacklisted_by_cb(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2, 'name': 'secret'}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__function__delete_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 1)
        self.assertTrue(isinstance(args[0], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id_consumer_callback_with_time_of_life

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])


class ViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []

    """
    🔽🔽🔽 View get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__anonymous_user(self):
        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission(self):
        permission = {'codename': PERMISSION}
        model = self.bc.database.create(user=1, permission=permission)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])


class ConsumerViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []

    """
    🔽🔽🔽 View get
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 View get id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 View post
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__anonymous_user(self):
        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 View put id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    """
    🔽🔽🔽 View delete id
    """

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumer.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])


class ConsumerCallbackViewTestSuite(UtilsTestCase):

    def setUp(self):
        super().setUp()
        CONSUMER_MOCK.call_args_list = []

    """
    🔽🔽🔽 View get
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = GET_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View get id
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__get_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = GET_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View post
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__anonymous_user(self):
        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__post__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {},
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request).render()
        expected = POST_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View put id
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__put_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = PUT_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    """
    🔽🔽🔽 View delete id
    """

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.assertEqual(CONSUMER_MOCK.call_args_list, [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__without_consumer(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        model = self.bc.database.create(user=user, permission=permissions, group=group)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_minus_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': -1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_0(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 0}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__with_group_related_to_permission__consumer__how_many_1(self):
        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallback.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallback))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__without_consumption_session(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user, permission=permissions, group=group, consumable=consumable)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__does_not_match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        Consumable = self.bc.database.get_model('payments.Consumable')
        consumables = Consumable.objects.filter()
        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        args, kwargs = CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list[0]
        context, args, kwargs = args

        self.assertTrue(isinstance(context['request'], Request))
        self.bc.check.partial_equality(context, {
            'utc_now': UTC_NOW,
            'consumer': CONSUMER_MOCK,
            'permission': PERMISSION,
            'consumables': consumables,
        })

        self.assertEqual(len(args), 2)
        self.assertTrue(isinstance(args[0], TestViewConsumerCallbackWithTimeOfLife))
        self.assertTrue(isinstance(args[1], Request))

        self.assertEqual(kwargs, {'id': 1})
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [
            call(instance=model.consumable, sender=model.consumable.__class__, how_many=1),
        ])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__does_not_match__consumables_minus_sessions_et_0(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        n = random.randint(1, 4)
        consumable = {'how_many': n}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'how_many': n,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])

        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])

    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.signals.consume_service.send', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.payments.models.ConsumptionSession.build_session',
           MagicMock(wraps=models.ConsumptionSession.build_session))
    def test__view__delete_id__with_user__consumption_session__match(self):
        CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list = []

        user = {'user_permissions': []}
        permissions = [{}, {'codename': PERMISSION}]
        group = {'permission_id': 2}
        consumable = {'how_many': 1}
        consumption_session = {
            'eta': UTC_NOW + time_of_life,
            'request': {
                'args': [],
                'kwargs': {
                    'id': 1
                },
                'headers': {
                    'academy': None
                },
                'user': 1
            }
        }
        model = self.bc.database.create(user=user,
                                        permission=permissions,
                                        group=group,
                                        consumable=consumable,
                                        consumption_session=consumption_session)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestViewConsumerCallbackWithTimeOfLife.as_view()

        response = view(request, id=1).render()
        expected = DELETE_ID_RESPONSE

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(CONSUMER_WITH_TIME_OF_LIFE_MOCK.call_args_list), 1)
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            self.bc.format.to_dict(model.consumption_session),
        ])

        self.assertEqual(models.ConsumptionSession.build_session.call_args_list, [])
        self.assertEqual(payments_signals.consume_service.send.call_args_list, [])
