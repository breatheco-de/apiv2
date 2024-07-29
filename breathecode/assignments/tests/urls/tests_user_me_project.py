"""
Test /final_project/<int:project_id>
"""

from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import AssignmentsTestCase


def put_serializer(self, project, data={}):
    return {
        "id": project.id,
        "logo_url": project.logo_url,
        "name": project.name,
        "one_line_desc": project.one_line_desc,
        "public_url": project.public_url,
        "cohort": project.cohort.id if project.cohort else None,
        "created_at": self.bc.datetime.to_iso_string(project.created_at),
        "description": project.description,
        "revision_status": project.revision_status,
        "revision_message": project.revision_message,
        **data,
    }


class FinalProjectTestSuite(AssignmentsTestCase):
    """Test /final_project"""

    """
    🔽🔽🔽 Auth
    """

    def test_final_project_with_no_auth(self):
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_final_project_with_wrong_id(self):

        self.bc.request.set_headers(academy=1)
        self.generate_models(
            authenticate=True,
            profile_academy=1,
            role=1,
        )
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})
        response = self.client.put(url)

        json = response.json()
        expected = {"detail": "project-not-found", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_final_project_when_not_a_member(self):

        self.bc.request.set_headers(academy=1)
        helper_models = self.bc.database.create(user=[{"id": 1}, {"id": 2}], cohort=1)
        project_cohort = helper_models["cohort"]

        models = self.bc.database.create(final_project={"members": [2]})
        self.bc.request.authenticate(helper_models["user"][0])
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})
        data = {"name": "Facebook", "cohort": project_cohort.id}
        response = self.client.put(url, data)

        json = response.json()
        expected = {"detail": "not-a-member", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_final_project_members_from_different_cohort(self):

        self.bc.request.set_headers(academy=1)
        helper_models = self.bc.database.create(user=[{"id": 1}, {"id": 2}], cohort=2)
        self.bc.request.authenticate(helper_models["user"][1])

        project_cohort = helper_models["cohort"][0]
        models = self.bc.database.create(
            cohort_user={"user": helper_models["user"][1], "cohort": helper_models["cohort"][1]},
            final_project={"members": [1, 2]},
        )
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})

        data = {"name": "Facebook", "members": [1, 2], "cohort": project_cohort.id}
        response = self.client.put(url, data)

        json = response.json()
        expected = {
            "detail": f"All members of this project must belong to the cohort {project_cohort.name} - 0",
            "status_code": 400,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_final_project_without_cohort(self):

        self.bc.request.set_headers(academy=1)
        helper_models = self.bc.database.create(user=[{"id": 1}, {"id": 2}])
        self.bc.request.authenticate(helper_models["user"][1])

        models = self.bc.database.create(final_project={"members": [1, 2]})
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})

        data = {"name": "Facebook", "members": [1, 2]}
        response = self.client.put(url, data)

        json = response.json()
        expected = {"detail": "cohort-missing", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("breathecode.admissions.signals.student_edu_status_updated.send_robust", MagicMock(return_value=None))
    def test_final_project(self):

        self.bc.request.set_headers(academy=1)
        helper_models = self.bc.database.create(user=1, cohort=1)
        cohort_user = self.bc.database.create(
            cohort_user={"user": helper_models["user"], "cohort": helper_models["cohort"]}
        )

        project_cohort = helper_models["cohort"]

        models = self.bc.database.create(final_project={"members": [helper_models["user"]], "cohort": project_cohort})

        self.bc.request.authenticate(helper_models["user"])
        url = reverse_lazy("assignments:user_me_project", kwargs={"project_id": 1})
        data = {"name": "Facebook", "cohort": project_cohort.id, "members": [1]}
        response = self.client.put(url, data)

        json = response.json()

        self.assertEqual(
            json,
            put_serializer(self, models["final_project"], {"name": "Facebook", "cohort": project_cohort.id, **json}),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
