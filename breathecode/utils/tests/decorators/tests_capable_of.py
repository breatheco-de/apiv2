from email import header
import json
from wsgiref import headers
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from breathecode.authenticate.models import ProfileAcademy
import breathecode.utils.decorators as decorators
from rest_framework.permissions import AllowAny
from rest_framework import status
from ..mixins import UtilsTestCase

PERMISSION = "can_kill_kenny"


@api_view(["GET"])
@permission_classes([AllowAny])
@decorators.capable_of(PERMISSION)
def get_id(request, id, academy_id=None):
    return Response({"id": id, "academy_id": academy_id})


class CustomTestView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    @decorators.capable_of(PERMISSION)
    def get(self, request, id, academy_id=None):
        return Response({"id": id, "academy_id": academy_id})


class FunctionBasedViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Function get id
    """

    def test_capable_of__function__get_id__anonymous_user(self):
        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny")

        view = get_id

        response = view(request, id=1).render()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__function__get_id__without_capability(self):
        model = self.bc.database.create(user=1)

        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {
            "detail": "You (user: 1) don't have this capability: can_kill_kenny for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__function__get_id__with_user__with_capability(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, role=1, capability="can_kill_kenny")

        factory = APIRequestFactory()
        request = factory.get("/they-killed-kenny", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {"academy_id": 1, "id": 1}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_capable_of__function__get_id__with_user__with_capability__status_inactive(self):
        academy_kwargs = {"status": "INACTIVE"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        factory = APIRequestFactory()
        slug_1 = self.bc.fake.slug()
        slug_2 = self.bc.fake.slug()
        request = factory.get(f"/{slug_1}/{slug_2}", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {"detail": "This academy is not active", "status_code": 403}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__function__get_id__with_user__with_capability__status_deleted(self):
        academy_kwargs = {"status": "DELETED"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        factory = APIRequestFactory()
        slug_1 = self.bc.fake.slug()
        slug_2 = self.bc.fake.slug()
        request = factory.get(f"/{slug_1}/{slug_2}", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {"detail": "This academy is deleted", "status_code": 403}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__function__get_id__with_user__with_capability__status_inactive_with_correct_link(self):
        academy_kwargs = {"status": "INACTIVE"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        factory = APIRequestFactory()
        request = factory.get("/v1/admissions/academy/activate", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {"academy_id": 1, "id": 1}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_capable_of__function__get_id__with_user__with_capability__status_deleted_with_correct_link(self):
        academy_kwargs = {"status": "DELETED"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        factory = APIRequestFactory()
        request = factory.get("/v1/admissions/academy/activate", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = get_id

        response = view(request, id=1).render()
        expected = {"detail": "This academy is deleted", "status_code": 403}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ViewTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 View get id
    """

    def test_capable_of__view__get__anonymous_user(self):
        request = APIRequestFactory()
        request = request.get("/they-killed-kenny")

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {
            "detail": "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            "status_code": 403,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__view__get_id__without_capability(self):
        model = self.bc.database.create(user=1)

        request = APIRequestFactory()
        request = request.get("/they-killed-kenny", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {
            "detail": "You (user: 1) don't have this capability: can_kill_kenny for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__view__get_id__with_user__with_capability(self):
        model = self.bc.database.create(user=1, academy=1, profile_academy=1, role=1, capability="can_kill_kenny")

        request = APIRequestFactory()
        request = request.get("/they-killed-kenny", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"id": 1, "academy_id": 1}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_capable_of__view__get_id__with_user__with_capability__academy_inactive(self):
        academy_kwargs = {"status": "INACTIVE"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        request = APIRequestFactory()
        slug_1 = self.bc.fake.slug()
        slug_2 = self.bc.fake.slug()
        request = request.get(f"/{slug_1}/{slug_2}", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"detail": "This academy is not active", "status_code": 403}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__view__get_id__with_user__with_capability__academy_deleted(self):
        academy_kwargs = {"status": "DELETED"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        request = APIRequestFactory()
        slug_1 = self.bc.fake.slug()
        slug_2 = self.bc.fake.slug()
        request = request.get(f"/{slug_1}/{slug_2}", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"detail": "This academy is deleted", "status_code": 403}
        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_capable_of__view__get_id__with_user__with_capability__academy_inactive_with_correct_link(self):
        academy_kwargs = {"status": "INACTIVE"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        request = APIRequestFactory()
        request = request.get("/v1/admissions/academy/activate", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"academy_id": 1, "id": 1}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_capable_of__view__get_id__with_user__with_capability__academy_deleted_with_correct_link(self):
        academy_kwargs = {"status": "DELETED"}
        model = self.bc.database.create(
            user=1, academy=academy_kwargs, profile_academy=1, role=1, capability="can_kill_kenny"
        )

        request = APIRequestFactory()
        request = request.get("/v1/admissions/academy/activate", headers={"academy": 1})
        force_authenticate(request, user=model.user)

        view = CustomTestView.as_view()

        response = view(request, id=1).render()
        expected = {"detail": "This academy is deleted", "status_code": 403}

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
