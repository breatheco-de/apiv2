"""
This file just can contains duck tests refert to AcademyInviteView
"""

from unittest.mock import MagicMock, patch

from django.urls.base import reverse_lazy
from rest_framework import status
from rest_framework.response import Response

from breathecode.utils import capable_of

from ...mixins.new_auth_test_case import AuthTestCase


@capable_of("invite_resend")
def view_method_mock(request, *args, **kwargs):
    response = {"args": args, "kwargs": kwargs}
    return Response(response, status=200)


# Duck test
class MemberGetDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """

    def test_duck_test__without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duck_test__without_capabilities(self):
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: read_invite for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_duck_test__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(authenticate=True, capability="read_invite", role="role", profile_academy=1)

            url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
            response = self.client.get(url)

            json = response.json()
            expected = {"detail": "user-invite-not-found", "status_code": 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch("breathecode.authenticate.views.AcademyInviteView.get", MagicMock(side_effect=view_method_mock))
    def test_duck_test__with_auth___mock_view(self):
        model = self.bc.database.create(
            academy=3,
            capability="invite_resend",
            role="role",
            profile_academy=[{"academy_id": id} for id in range(1, 4)],
        )

        for n in range(1, 4):
            self.client.force_authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": n})
            response = self.client.get(url)
            json = response.json()
            expected = {"args": [], "kwargs": {"academy_id": "1", "invite_id": n}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# Duck test
class MemberPutDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """

    def test_academy_id_member_id_without_auth(self):
        """Test /academy/:id/member without auth"""
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_id_member_id__without_capabilities(self):
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.put(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: invite_resend for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.all_cohort_time_slot_dict(), [])

    def test_academy_id_member_id__with_auth(self):
        for n in range(1, 4):
            self.bc.request.set_headers(academy=n)
            model = self.bc.database.create(
                authenticate=True, capability="invite_resend", role="role", profile_academy=1
            )

            url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
            response = self.client.put(url)

            json = response.json()
            expected = {"detail": "user-invite-not-found", "status_code": 404}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 Check the param is being passed
    """

    @patch("breathecode.authenticate.views.AcademyInviteView.put", MagicMock(side_effect=view_method_mock))
    def test_academy_id_member_id__with_auth___mock_view(self):
        model = self.bc.database.create(
            academy=3,
            capability="invite_resend",
            role="role",
            profile_academy=[{"academy_id": id} for id in range(1, 4)],
        )

        for n in range(1, 4):
            self.client.force_authenticate(model.user)
            self.bc.request.set_headers(academy=1)

            url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": n})
            response = self.client.put(url)
            json = response.json()
            expected = {"args": [], "kwargs": {"academy_id": "1", "invite_id": n}}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


# Duck test
class MemberPatchDuckTestSuite(AuthTestCase):
    """
    🔽🔽🔽 Check decorator
    """

    def test_academy_invite_id_patch__without_auth(self):
        """Test PATCH /academy/invite/:id without auth"""
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.patch(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "Authentication credentials were not provided.",
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_academy_invite_id_patch__without_capabilities(self):
        self.bc.request.set_headers(academy=1)
        model = self.bc.database.create(authenticate=True)
        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 1})
        response = self.client.patch(url)
        json = response.json()

        self.assertEqual(
            json,
            {
                "detail": "You (user: 1) don't have this capability: crud_invite for academy 1",
                "status_code": 403,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_academy_invite_id_patch__without_invite_id(self):
        """Test PATCH /academy/user/invite without invite_id"""
        model = self.bc.database.create(
            authenticate=True, capability="crud_invite", role="role", profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_user_invite")
        response = self.client.patch(url)
        json = response.json()

        self.assertEqual(json["detail"], "invite-id-required")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_academy_invite_id_patch__invite_not_found(self):
        """Test PATCH /academy/invite/:id with non-existent invite"""
        model = self.bc.database.create(
            authenticate=True, capability="crud_invite", role="role", profile_academy=1
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": 999})
        response = self.client.patch(url)
        json = response.json()

        self.assertEqual(json["detail"], "user-invite-not-found")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_academy_invite_id_patch__reset_to_pending(self):
        """Test PATCH /academy/invite/:id resets status to PENDING and generates new token"""
        user_invite = {"status": "ACCEPTED", "token": "old-token-123"}
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_invite",
            role="role",
            profile_academy=1,
            user_invite=user_invite,
        )

        old_token = model.user_invite.token
        old_status = model.user_invite.status

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": model.user_invite.id})
        response = self.client.patch(url, {"status": "PENDING"}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["status"], "PENDING")
        self.assertNotEqual(json["token"], old_token)
        self.assertNotEqual(json["status"], old_status)

        # Verify in database
        model.user_invite.refresh_from_db()
        self.assertEqual(model.user_invite.status, "PENDING")
        self.assertNotEqual(model.user_invite.token, old_token)
        self.assertIsNone(model.user_invite.sent_at)

    def test_academy_invite_id_patch__update_to_accepted_no_token_reset(self):
        """Test PATCH /academy/invite/:id updates status to ACCEPTED without resetting token"""
        user_invite = {"status": "PENDING", "token": "original-token-123"}
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_invite",
            role="role",
            profile_academy=1,
            user_invite=user_invite,
        )

        old_token = model.user_invite.token

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": model.user_invite.id})
        response = self.client.patch(url, {"status": "ACCEPTED"}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["status"], "ACCEPTED")
        # Token should remain the same
        self.assertEqual(json["token"], old_token)

        # Verify in database
        model.user_invite.refresh_from_db()
        self.assertEqual(model.user_invite.status, "ACCEPTED")
        self.assertEqual(model.user_invite.token, old_token)

    def test_academy_invite_id_patch__invalid_status(self):
        """Test PATCH /academy/invite/:id with invalid status"""
        user_invite = {"status": "PENDING"}
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_invite",
            role="role",
            profile_academy=1,
            user_invite=user_invite,
        )

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": model.user_invite.id})
        response = self.client.patch(url, {"status": "INVALID_STATUS"}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json["detail"], "invalid-status")

    def test_academy_invite_id_patch__no_status_provided(self):
        """Test PATCH /academy/invite/:id without status (no changes)"""
        user_invite = {"status": "ACCEPTED", "token": "original-token-123"}
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_invite",
            role="role",
            profile_academy=1,
            user_invite=user_invite,
        )

        old_token = model.user_invite.token
        old_status = model.user_invite.status

        self.bc.request.set_headers(academy=1)
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": model.user_invite.id})
        response = self.client.patch(url, {}, format="json")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Status and token should remain unchanged
        self.assertEqual(json["status"], old_status)
        self.assertEqual(json["token"], old_token)

        # Verify in database
        model.user_invite.refresh_from_db()
        self.assertEqual(model.user_invite.status, old_status)
        self.assertEqual(model.user_invite.token, old_token)

    def test_academy_invite_id_patch__invite_from_different_academy(self):
        """Test PATCH /academy/invite/:id with invite from different academy"""
        user_invite = {"academy_id": 2}
        model = self.bc.database.create(
            authenticate=True,
            capability="crud_invite",
            role="role",
            profile_academy=1,
            user_invite=user_invite,
            academy=2,
        )

        self.bc.request.set_headers(academy=1)  # Different academy
        self.client.force_authenticate(model.user)

        url = reverse_lazy("authenticate:academy_invite_id", kwargs={"invite_id": model.user_invite.id})
        response = self.client.patch(url)
        json = response.json()

        self.assertEqual(json["detail"], "user-invite-not-found")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
