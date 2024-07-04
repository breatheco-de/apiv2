import os

from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from rest_framework import status
import breathecode.authenticate.management.commands.create_academy_roles as create_academy_roles

from ..mixins import CypressTestCase

CAPABILITIES = [
    {"slug": "read_my_academy", "description": "Read your academy information"},
    {
        "slug": "crud_my_academy",
        "description": "Read, or update your academy information (very high level, almost the academy admin)",
    },
    {
        "slug": "crud_member",
        "description": "Create, update or delete academy members (very high level, almost the academy admin)",
    },
    {"slug": "read_member", "description": "Read academy staff member information"},
    {"slug": "crud_student", "description": "Create, update or delete students"},
    {"slug": "read_student", "description": "Read student information"},
    {"slug": "read_invite", "description": "Read invites from users"},
    {"slug": "read_assignment", "description": "Read assigment information"},
    {
        "slug": "read_assignment_sensitive_details",
        "description": 'The mentor in residence is allowed to see aditional info about the task, like the "delivery url"',
    },
    {"slug": "read_shortlink", "description": "Access the list of marketing shortlinks"},
    {"slug": "crud_shortlink", "description": "Create, update and delete marketing short links"},
    {"slug": "crud_assignment", "description": "Create, update or delete a assigment"},
    {
        "slug": "task_delivery_details",
        "description": "Get delivery URL for a task, that url can be sent to students for delivery",
    },
    {"slug": "read_certificate", "description": "List and read all academy certificates"},
    {"slug": "crud_certificate", "description": "Create, update or delete student certificates"},
    {"slug": "read_layout", "description": "Read layouts to generate new certificates"},
    {"slug": "read_syllabus", "description": "List and read syllabus information"},
    {"slug": "crud_syllabus", "description": "Create, update or delete syllabus versions"},
    {"slug": "read_event", "description": "List and retrieve event information"},
    {"slug": "crud_event", "description": "Create, update or delete event information"},
    {"slug": "read_all_cohort", "description": "List all the cohorts or a single cohort information"},
    {"slug": "crud_cohort", "description": "Create, update or delete cohort info"},
    {"slug": "read_eventcheckin", "description": "List and read all the event_checkins"},
    {"slug": "read_survey", "description": "List all the nps answers"},
    {"slug": "crud_survey", "description": "Create, update or delete surveys"},
    {"slug": "read_nps_answers", "description": "List all the nps answers"},
    {"slug": "read_lead", "description": "List all the leads"},
    {"slug": "read_won_lead", "description": "List all the won leads"},
    {"slug": "crud_lead", "description": "Create, update or delete academy leads"},
    {"slug": "read_review", "description": "Read review for a particular academy"},
    {"slug": "crud_review", "description": "Create, update or delete academy reviews"},
    {"slug": "read_media", "description": "List all the medias"},
    {"slug": "crud_media", "description": "Create, update or delete academy medias"},
    {"slug": "read_media_resolution", "description": "List all the medias resolutions"},
    {"slug": "crud_media_resolution", "description": "Create, update or delete academy media resolutions"},
    {"slug": "read_cohort_activity", "description": "Read low level activity in a cohort (attendancy, etc.)"},
    {"slug": "generate_academy_token", "description": "Create a new token only to be used by the academy"},
    {"slug": "get_academy_token", "description": "Read the academy token"},
    {"slug": "send_reset_password", "description": "Generate a temporal token and resend forgot password link"},
    {"slug": "read_activity", "description": "List all the user activities"},
    {"slug": "crud_activity", "description": "Create, update or delete a user activities"},
    {"slug": "read_assigment", "description": "List all the assigments"},
    {
        "slug": "classroom_activity",
        "description": "To report student activities during the classroom or cohorts (Specially meant for teachers)",
    },
    {"slug": "academy_reporting", "description": "Get detailed reports about the academy activity"},
    {
        "slug": "generate_temporal_token",
        "description": "Generate a temporal token to reset github credential or forgot password",
    },
    {"slug": "read_mentorship_service", "description": "Get all mentorship services from one academy"},
    {"slug": "read_mentorship_mentor", "description": "Get all mentorship mentors from one academy"},
    {"slug": "read_mentorship_session", "description": "Get all session from one academy"},
    {"slug": "crud_mentorship_session", "description": "Get all session from one academy"},
    {"slug": "read_mentor", "description": "Get update academy mentors"},
    {"slug": "crud_mentor", "description": "Update, create and delete academy mentors"},
    {"slug": "crud_asset", "description": "Update, create and delete registry assets"},
    {"slug": "read_tag", "description": "Read marketing tags and their details"},
    {"slug": "crud_tag", "description": "Update, create and delete a marketing tag and its details"},
]

ROLES = [
    {
        "slug": "admin",
        "name": "Admin",
        "caps": [c["slug"] for c in CAPABILITIES],
    },
    {
        "slug": "academy_token",
        "name": "Academy Token",
        "caps": [
            "read_member",
            "read_syllabus",
            "read_student",
            "read_all_cohort",
            "read_media",
            "read_my_academy",
            "read_invite",
            "read_lead",
            "crud_lead",
            "read_review",
            "read_shortlink",
            "read_mentorship_service",
            "read_mentorship_mentor",
        ],
    },
    {
        "slug": "staff",
        "name": "Staff (Base)",
        "caps": [
            "read_member",
            "read_syllabus",
            "read_student",
            "read_all_cohort",
            "read_media",
            "read_my_academy",
            "read_invite",
            "get_academy_token",
            "crud_activity",
            "read_survey",
            "read_layout",
            "read_event",
            "read_certificate",
            "academy_reporting",
            "read_won_lead",
            "read_eventcheckin",
            "read_review",
            "read_activity",
            "read_shortlink",
            "read_mentorship_service",
            "read_mentorship_mentor",
        ],
    },
    {
        "slug": "student",
        "name": "Student",
        "caps": [
            "crud_assignment",
            "read_syllabus",
            "read_assignment",
            "read_all_cohort",
            "read_my_academy",
            "crud_activity",
            "read_mentorship_service",
            "read_mentorship_mentor",
        ],
    },
]


def extend_roles(roles: list):
    roles.append(
        {
            "slug": "assistant",
            "name": "Teacher Assistant",
            "caps": create_academy_roles.extend(roles, ["staff"])
            + [
                "read_assigment",
                "crud_assignment",
                "read_cohort_activity",
                "read_nps_answers",
                "classroom_activity",
                "read_event",
                "task_delivery_details",
                "crud_cohort",
            ],
        }
    )
    roles.append(
        {
            "slug": "career_support",
            "name": "Career Support Specialist",
            "caps": create_academy_roles.extend(roles, ["staff"])
            + ["read_certificate", "crud_certificate", "crud_shortlink"],
        }
    )
    roles.append(
        {
            "slug": "admissions_developer",
            "name": "Admissions Developer",
            "caps": create_academy_roles.extend(roles, ["staff"])
            + ["crud_lead", "crud_student", "crud_cohort", "read_all_cohort", "read_lead", "read_activity"],
        }
    )
    roles.append(
        {
            "slug": "syllabus_coordinator",
            "name": "Syllabus Coordinator",
            "caps": create_academy_roles.extend(roles, ["staff"]) + ["crud_syllabus", "crud_media", "crud_asset"],
        }
    )
    roles.append(
        {
            "slug": "culture_and_recruitment",
            "name": "Culture and Recruitment",
            "caps": create_academy_roles.extend(roles, ["staff"]) + ["crud_member"],
        }
    )
    roles.append(
        {
            "slug": "community_manager",
            "name": "Manage Syllabus, Exercises and all academy content",
            "caps": create_academy_roles.extend(roles, ["staff"])
            + [
                "crud_lead",
                "read_event",
                "crud_event",
                "read_eventcheckin",
                "read_nps_answers",
                "read_lead",
                "read_all_cohort",
                "crud_media",
            ],
        }
    )
    roles.append(
        {
            "slug": "growth_manager",
            "name": "Growth Manager",
            "caps": create_academy_roles.extend(roles, ["staff", "community_manager"])
            + [
                "crud_media",
                "read_activity",
                "read_lead",
                "read_won_lead",
                "crud_review",
                "crud_shortlink",
                "crud_tag",
            ],
        }
    )
    roles.append(
        {
            "slug": "homework_reviewer",
            "name": "Homework Reviewer",
            "caps": create_academy_roles.extend(roles, ["assistant"]),
        }
    )
    roles.append(
        {
            "slug": "teacher",
            "name": "Teacher",
            "caps": create_academy_roles.extend(roles, ["assistant"]) + ["crud_cohort"],
        }
    )
    roles.append(
        {
            "slug": "academy_coordinator",
            "name": "Mentor in residence",
            "caps": create_academy_roles.extend(roles, ["teacher"])
            + [
                "crud_syllabus",
                "crud_cohort",
                "crud_student",
                "crud_survey",
                "read_won_lead",
                "crud_member",
                "send_reset_password",
                "generate_temporal_token",
                "crud_certificate",
                "crud_review",
                "crud_mentor",
                "read_mentor",
                "read_assignment_sensitive_details",
                "crud_shortlink",
            ],
        }
    )
    roles.append(
        {
            "slug": "country_manager",
            "name": "Country Manager",
            "caps": create_academy_roles.extend(
                roles,
                [
                    "academy_coordinator",
                    "student",
                    "career_support",
                    "growth_manager",
                    "admissions_developer",
                    "syllabus_coordinator",
                    "read_organization",
                    "crud_organization",
                ],
            )
            + ["crud_my_academy", "generate_academy_token", "send_reset_password", "generate_temporal_token"],
        }
    )


class AcademyEventTestSuite(CypressTestCase):

    def test_load_roles__bad_environment__not_exits(self):
        if "ALLOW_UNSAFE_CYPRESS_APP" in os.environ:
            del os.environ["ALLOW_UNSAFE_CYPRESS_APP"]

        url = reverse_lazy("cypress:load_roles")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_role_dict(), [])
        self.assertEqual(self.all_capability_dict(), [])

    def test_load_roles__bad_environment__empty_string(self):
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = ""

        url = reverse_lazy("cypress:load_roles")
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "is-not-allowed", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_role_dict(), [])
        self.assertEqual(self.all_capability_dict(), [])

    @patch(
        "breathecode.authenticate.management.commands.create_academy_roles.get_capabilities",
        MagicMock(return_value=CAPABILITIES),
    )
    @patch("breathecode.authenticate.management.commands.create_academy_roles.get_roles", MagicMock(return_value=ROLES))
    @patch(
        "breathecode.authenticate.management.commands.create_academy_roles.extend_roles",
        MagicMock(side_effect=extend_roles),
    )
    def test_load_roles(self):
        self.maxDiff = None
        os.environ["ALLOW_UNSAFE_CYPRESS_APP"] = "True"
        url = reverse_lazy("cypress:load_roles")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.all_role_dict(),
            [
                {
                    "slug": "admin",
                    "name": "Admin",
                },
                {
                    "slug": "academy_token",
                    "name": "Academy Token",
                },
                {
                    "slug": "staff",
                    "name": "Staff (Base)",
                },
                {
                    "slug": "student",
                    "name": "Student",
                },
                {
                    "slug": "assistant",
                    "name": "Teacher Assistant",
                },
                {
                    "slug": "career_support",
                    "name": "Career Support Specialist",
                },
                {
                    "slug": "admissions_developer",
                    "name": "Admissions Developer",
                },
                {
                    "slug": "syllabus_coordinator",
                    "name": "Syllabus Coordinator",
                },
                {
                    "slug": "culture_and_recruitment",
                    "name": "Culture and Recruitment",
                },
                {
                    "slug": "community_manager",
                    "name": "Manage Syllabus, Exercises and all academy content",
                },
                {
                    "slug": "growth_manager",
                    "name": "Growth Manager",
                },
                {
                    "slug": "homework_reviewer",
                    "name": "Homework Reviewer",
                },
                {
                    "slug": "teacher",
                    "name": "Teacher",
                },
                {
                    "slug": "academy_coordinator",
                    "name": "Mentor in residence",
                },
                {
                    "slug": "country_manager",
                    "name": "Country Manager",
                },
            ],
        )

        self.assertEqual(
            self.all_capability_dict(),
            [
                {"slug": "read_my_academy", "description": "Read your academy information"},
                {
                    "slug": "crud_my_academy",
                    "description": "Read, or update your academy information (very high level, almost the academy admin)",
                },
                {
                    "slug": "crud_member",
                    "description": "Create, update or delete academy members (very high level, almost the academy admin)",
                },
                {"slug": "read_member", "description": "Read academy staff member information"},
                {"slug": "crud_student", "description": "Create, update or delete students"},
                {"slug": "read_student", "description": "Read student information"},
                {"slug": "read_invite", "description": "Read invites from users"},
                {"slug": "read_assignment", "description": "Read assigment information"},
                {
                    "description": "The mentor in residence is allowed to see aditional info "
                    'about the task, like the "delivery url"',
                    "slug": "read_assignment_sensitive_details",
                },
                {"description": "Access the list of marketing shortlinks", "slug": "read_shortlink"},
                {"description": "Create, update and delete marketing short links", "slug": "crud_shortlink"},
                {"slug": "crud_assignment", "description": "Create, update or delete a assigment"},
                {
                    "description": ("Get delivery URL for a task, that url can be sent to " "students for delivery"),
                    "slug": "task_delivery_details",
                },
                {"slug": "read_certificate", "description": "List and read all academy certificates"},
                {"slug": "crud_certificate", "description": "Create, update or delete student certificates"},
                {"slug": "read_layout", "description": "Read layouts to generate new certificates"},
                {"slug": "read_syllabus", "description": "List and read syllabus information"},
                {"slug": "crud_syllabus", "description": "Create, update or delete syllabus versions"},
                {"slug": "read_event", "description": "List and retrieve event information"},
                {"slug": "crud_event", "description": "Create, update or delete event information"},
                {"slug": "read_all_cohort", "description": "List all the cohorts or a single cohort information"},
                {"slug": "crud_cohort", "description": "Create, update or delete cohort info"},
                {"slug": "read_eventcheckin", "description": "List and read all the event_checkins"},
                {"slug": "read_survey", "description": "List all the nps answers"},
                {"slug": "crud_survey", "description": "Create, update or delete surveys"},
                {"slug": "read_nps_answers", "description": "List all the nps answers"},
                {"slug": "read_lead", "description": "List all the leads"},
                {"slug": "read_won_lead", "description": "List all the won leads"},
                {"slug": "crud_lead", "description": "Create, update or delete academy leads"},
                {"slug": "read_review", "description": "Read review for a particular academy"},
                {"slug": "crud_review", "description": "Create, update or delete academy reviews"},
                {"slug": "read_media", "description": "List all the medias"},
                {"slug": "crud_media", "description": "Create, update or delete academy medias"},
                {"slug": "read_media_resolution", "description": "List all the medias resolutions"},
                {"slug": "crud_media_resolution", "description": "Create, update or delete academy media resolutions"},
                {
                    "slug": "read_cohort_activity",
                    "description": "Read low level activity in a cohort (attendancy, etc.)",
                },
                {"slug": "generate_academy_token", "description": "Create a new token only to be used by the academy"},
                {"slug": "get_academy_token", "description": "Read the academy token"},
                {
                    "slug": "send_reset_password",
                    "description": "Generate a temporal token and resend forgot password link",
                },
                {"slug": "read_activity", "description": "List all the user activities"},
                {"slug": "crud_activity", "description": "Create, update or delete a user activities"},
                {"slug": "read_assigment", "description": "List all the assigments"},
                {
                    "slug": "classroom_activity",
                    "description": "To report student activities during the classroom or cohorts (Specially meant for teachers)",
                },
                {"slug": "academy_reporting", "description": "Get detailed reports about the academy activity"},
                {
                    "slug": "generate_temporal_token",
                    "description": "Generate a temporal token to reset github credential or forgot password",
                },
                {"slug": "read_mentorship_service", "description": "Get all mentorship services from one academy"},
                {"slug": "read_mentorship_mentor", "description": "Get all mentorship mentors from one academy"},
                {"slug": "read_mentorship_session", "description": "Get all session from one academy"},
                {
                    "slug": "crud_mentorship_session",
                    "description": "Get all session from one academy",
                },
                {"slug": "read_mentor", "description": "Get update academy mentors"},
                {"slug": "crud_mentor", "description": "Update, create and delete academy mentors"},
                {"description": "Update, create and delete registry assets", "slug": "crud_asset"},
                {"slug": "read_tag", "description": "Read marketing tags and their details"},
                {"slug": "crud_tag", "description": "Update, create and delete a marketing tag and its details"},
            ],
        )

    def test_load_roles__check_the_capabilities(self):
        from ....authenticate.management.commands.create_academy_roles import CAPABILITIES

        for capability in CAPABILITIES:
            self.assertRegex(capability["slug"], r"^[a-z_]+$")
            self.assertRegex(capability["description"], r'^[a-zA-Z,. _()"]+$')
            self.assertEqual(len(capability), 2)

    def test_load_roles__check_the_roles(self):
        from ....authenticate.management.commands.create_academy_roles import ROLES

        for role in ROLES:
            self.assertRegex(role["slug"], r"^[a-z_]+$")
            self.assertRegex(role["name"], r'^[a-zA-Z. ()"]+$')

            for capability in role["caps"]:
                self.assertRegex(capability, r"^[a-z_]+$")

            self.assertEqual(len(role), 3)
