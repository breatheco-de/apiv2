"""
Test cases for /academy/:id/member/:id
"""

import os
import urllib.parse

from django.template import loader
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins.new_auth_test_case import AuthTestCase


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_page_without_invites():
    request = None
    APP_URL = os.getenv("APP_URL", "")[:-1]

    return loader.render_to_string(
        "message.html",
        {
            "MESSAGE": f"You don't have any more pending invites",
            "BUTTON": "Continue to 4Geeks",
            "BUTTON_TARGET": "_blank",
            "LINK": APP_URL,
        },
        request,
    )


def render_page_with_pending_invites(self, model):
    request = None
    APP_URL = os.getenv("APP_URL", "")[:-1]
    user_invites = []
    if "user_invite" in model:
        user_invites = model.user_invite if isinstance(model.user_invite, list) else [model.user_invite]

    # excluding the accepted invited
    user_invites = [x for x in user_invites if x.status != "ACCEPTED"]

    querystr = urllib.parse.urlencode({"callback": APP_URL, "token": model.token.key})
    url = os.getenv("API_URL") + "/v1/auth/member/invite?" + querystr
    return loader.render_to_string(
        "user_invite.html",
        {
            "subject": f"Invitation to study at 4Geeks.com",
            "invites": [
                {
                    "id": user_invite.id,
                    "academy": (
                        {
                            "id": user_invite.academy.id,
                            "name": user_invite.academy.name,
                            "slug": user_invite.academy.slug,
                            "timezone": user_invite.academy.timezone,
                        }
                        if user_invite.academy
                        else None
                    ),
                    "cohort": (
                        {
                            "id": user_invite.cohort.id,
                            "name": user_invite.cohort.name,
                            "slug": user_invite.cohort.slug,
                            "ending_date": (
                                self.bc.datetime.to_iso_string(user_invite.cohort.ending_date)
                                if user_invite.cohort.ending_date
                                else None
                            ),
                            "stage": user_invite.cohort.stage,
                        }
                        if user_invite.cohort
                        else None
                    ),
                    "role": user_invite.role.slug if user_invite.role else None,
                    "created_at": user_invite.created_at,
                }
                for user_invite in user_invites
            ],
            "LINK": url,
            "user": {
                "id": model.user.id,
                "email": model.user.email,
                "first_name": model.user.first_name,
            },
        },
        request,
    )


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""

    """
    🔽🔽🔽 Auth
    """

    def test_member_invite__without_auth(self):
        url = reverse_lazy("authenticate:member_invite")
        response = self.client.get(url)

        hash = self.bc.format.to_base64("/v1/auth/member/invite")
        content = self.bc.format.from_bytes(response.content)
        expected = ""

        self.assertEqual(content, expected)
        self.assertEqual(response.url, f"/v1/auth/view/login?attempt=1&url={hash}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])
        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET without UserInvite
    """

    def test_member_invite__without_profile_academy(self):
        model = self.bc.database.create(user=1, token=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_without_invites()

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), [])

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with one UserInvite
    """

    def test_member_invite__with_one_profile_academy(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=user)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(self, model)

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                self.bc.format.to_dict(model.user_invite),
            ],
        )

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with two UserInvite without Academy, Cohort and Role
    """

    def test_member_invite__with_two_profile_academy(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=(2, user))

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(self, model)

        # dump error in external files
        if content != expected or 1:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), self.bc.format.to_dict(model.user_invite))

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with two UserInvite with Academy and Role, without Cohort
    """

    def test_member_invite__with_two_profile_academy__with_academy_and_role(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=(2, user), academy=1, role=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(self, model)

        # dump error in external files
        if content != expected or 1:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), self.bc.format.to_dict(model.user_invite))

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with two UserInvite without Academy and Role, with Cohort
    """

    def test_member_invite__with_two_profile_academy__with_cohort(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=(2, user), cohort=1)

        querystring = self.bc.format.to_querystring({"token": model.token.key})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_with_pending_invites(self, model)

        # dump error in external files
        if content != expected or 1:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("authenticate.UserInvite"), self.bc.format.to_dict(model.user_invite))

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with two UserInvite, accepting both
    """

    def test_member_invite__with_two_profile_academy__accepting_both(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=(2, user))

        querystring = self.bc.format.to_querystring({"token": model.token.key, "accepting": "1,2"})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_without_invites()

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(user_invite),
                    "status": "ACCEPTED",
                    "user_id": 1,
                }
                for user_invite in model.user_invite
            ],
        )

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])

    """
    🔽🔽🔽 GET with two UserInvite, rejecting both
    """

    def test_member_invite__with_two_profile_academy__rejecting_both(self):
        user = {"email": "dr-goku@yt.com"}
        model = self.bc.database.create(user=user, token=1, user_invite=(2, user))

        querystring = self.bc.format.to_querystring({"token": model.token.key, "rejecting": "1,2"})
        url = reverse_lazy("authenticate:member_invite") + f"?{querystring}"
        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_page_without_invites()

        # dump error in external files
        if content != expected:
            with open("content.html", "w") as f:
                f.write(content)

            with open("expected.html", "w") as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("authenticate.UserInvite"),
            [
                {
                    **self.bc.format.to_dict(user_invite),
                    "status": "REJECTED",
                }
                for user_invite in model.user_invite
            ],
        )

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.assertEqual(self.bc.database.list_of("admissions.CohortUser"), [])
