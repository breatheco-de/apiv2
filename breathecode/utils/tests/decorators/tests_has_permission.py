import json
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
import breathecode.utils.decorators as decorators
from rest_framework.permissions import AllowAny
from rest_framework import status
from ..mixins import UtilsTestCase

PERMISSION = 'can_kill_kenny'
GET_RESPONSE = {'a': 1}
GET_ID_RESPONSE = {'a': 2}
POST_RESPONSE = {'a': 3}
PUT_ID_RESPONSE = {'a': 4}
DELETE_ID_RESPONSE = {'a': 5}


@api_view(['GET'])
@permission_classes([AllowAny])
@decorators.has_permission(PERMISSION)
def get(request):
    return Response(GET_RESPONSE)


@api_view(['GET'])
@permission_classes([AllowAny])
@decorators.has_permission(PERMISSION)
def get_id(request, id):
    return Response(GET_ID_RESPONSE)


@api_view(['POST'])
@permission_classes([AllowAny])
@decorators.has_permission(PERMISSION)
def post(request):
    return Response(POST_RESPONSE)


@api_view(['PUT'])
@permission_classes([AllowAny])
@decorators.has_permission(PERMISSION)
def put_id(request, id):
    return Response(PUT_ID_RESPONSE)


@api_view(['DELETE'])
@permission_classes([AllowAny])
@decorators.has_permission(PERMISSION)
def delete_id(request, id):
    return Response(DELETE_ID_RESPONSE)


class TestView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    permission_classes = [AllowAny]

    @decorators.has_permission(PERMISSION)
    def get(self, request, id=None):
        if id:
            return Response(GET_ID_RESPONSE)

        return Response(GET_RESPONSE)

    @decorators.has_permission(PERMISSION)
    def post(self, request):
        return Response(POST_RESPONSE)

    @decorators.has_permission(PERMISSION)
    def put(self, request, id):
        return Response(PUT_ID_RESPONSE)

    @decorators.has_permission(PERMISSION)
    def delete(self, request, id=None):
        return Response(DELETE_ID_RESPONSE)


class FunctionBasedViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Function get
    """

    def test_has_permission__function__get__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get__with_user__with_permission(self):
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

    def test_has_permission__function__get__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 Function get id
    """

    def test_has_permission__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__get_id__with_user__with_permission(self):
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

    def test_has_permission__function__get_id__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 Function post
    """

    def test_has_permission__function__post__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')

        view = post

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__post__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = post

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__post__with_user__with_permission(self):
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

    def test_has_permission__function__post__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 Function put id
    """

    def test_has_permission__function__put_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = put_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__put_id__with_user__with_permission(self):
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

    def test_has_permission__function__put_id__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 Function delete id
    """

    def test_has_permission__function__delete_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        factory = APIRequestFactory()
        request = factory.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = delete_id

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__function__delete_id__with_user__with_permission(self):
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

    def test_has_permission__function__delete_id__with_user__with_group_related_to_permission(self):
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


class ViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 View get
    """

    def test_has_permission__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get__with_user__with_permission(self):
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

    def test_has_permission__view__get__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 View get id
    """

    def test_has_permission__view__get_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.get('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__get_id__with_user__with_permission(self):
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

    def test_has_permission__view__get_id__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 View post
    """

    def test_has_permission__view__post__anonymous_user(self):
        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__post__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__post__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.post('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__post__with_user__with_permission(self):
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

    def test_has_permission__view__post__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 View put id
    """

    def test_has_permission__view__put_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__put_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__put_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.put('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__put_id__with_user__with_permission(self):
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

    def test_has_permission__view__put_id__with_user__with_group_related_to_permission(self):
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

    """
    🔽🔽🔽 View delete id
    """

    def test_has_permission__view__delete_id__anonymous_user(self):
        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'anonymous-user-without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__delete_id__with_user(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__delete_id__with_user__with_permission__dont_match(self):
        model = self.bc.database.create(user=1, permission=1)

        request = APIRequestFactory()
        request = request.delete('/they-killed-kenny')
        force_authenticate(request, user=model.user)

        view = TestView.as_view()

        response = view(request, id=1).render()
        expected = {'detail': 'without-permission', 'status_code': 403}

        self.assertEqual(json.loads(response.content.decode('utf-8')), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_permission__view__delete_id__with_user__with_permission(self):
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

    def test_has_permission__view__delete_id__with_user__with_group_related_to_permission(self):
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
