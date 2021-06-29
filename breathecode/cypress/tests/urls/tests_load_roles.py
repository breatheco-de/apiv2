import os

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import CypressTestCase


class AcademyEventTestSuite(CypressTestCase):
    def test_load_roles__bad_environment__not_exits(self):
        if 'ALLOW_UNSAFE_CYPRESS_APP' in os.environ:
            del os.environ['ALLOW_UNSAFE_CYPRESS_APP']

        url = reverse_lazy('cypress:load_roles')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_role_dict(), [])
        self.assertEqual(self.all_capability_dict(), [])

    def test_load_roles__bad_environment__empty_string(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = ''

        url = reverse_lazy('cypress:load_roles')
        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'is-not-allowed', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.all_role_dict(), [])
        self.assertEqual(self.all_capability_dict(), [])

    def test_load_roles(self):
        os.environ['ALLOW_UNSAFE_CYPRESS_APP'] = 'True'
        url = reverse_lazy('cypress:load_roles')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.all_role_dict(), [
            {
                'slug': 'admin',
                'name': 'Admin',
            },
            {
                'slug': 'academy_token',
                'name': 'Academy Token',
            },
            {
                'slug': 'staff',
                'name': 'Staff (Base)',
            },
            {
                'slug': 'student',
                'name': 'Student',
            },
            {
                'slug': 'assistant',
                'name': 'Teacher Assistant',
            },
            {
                'slug': 'career_support',
                'name': 'Career Support Specialist',
            },
            {
                'slug': 'admissions_developer',
                'name': 'Admissions Developer',
            },
            {
                'slug': 'syllabus_coordinator',
                'name': 'Syllabus Coordinator',
            },
            {
                'slug': 'culture_and_recruitment',
                'name': 'Culture and Recruitment',
            },
            {
                'slug': 'community_manager',
                'name': 'Manage Syllabus, Exercises and all academy content',
            },
            {
                'slug': 'growth_manager',
                'name': 'Growth Manager',
            },
            {
                'slug': 'homework_reviewer',
                'name': 'Homework Reviewer',
            },
            {
                'slug': 'teacher',
                'name': 'Teacher',
            },
            {
                'slug': 'academy_coordinator',
                'name': 'Mentor in residence',
            },
            {
                'slug': 'country_manager',
                'name': 'Country Manager',
            },
        ])

        self.assertEqual(self.all_capability_dict(), [
            {
                'slug': 'read_my_academy',
                'description': 'Read your academy information',
            },
            {
                'slug':
                'crud_my_academy',
                'description':
                'Read, or update your academy information (very high level, almost the academy admin)',
            },
            {
                'slug':
                'crud_member',
                'description':
                'Create, update or delete academy members (very high level, almost the academy admin)',
            },
            {
                'slug': 'read_member',
                'description': 'Read academy staff member information',
            },
            {
                'slug': 'crud_student',
                'description': 'Create, update or delete students',
            },
            {
                'slug': 'read_student',
                'description': 'Read student information',
            },
            {
                'slug': 'read_invite',
                'description': 'Read invites from users',
            },
            {
                'slug': 'read_assignment',
                'description': 'Read assigment information',
            },
            {
                'slug': 'crud_assignment',
                'description': 'Update assignments',
            },
            {
                'slug': 'read_certificate',
                'description': 'List and read all academy certificates',
            },
            {
                'slug': 'crud_certificate',
                'description': 'Create, update or delete student certificates',
            },
            {
                'slug': 'read_syllabus',
                'description': 'List and read syllabus information',
            },
            {
                'slug': 'crud_syllabus',
                'description': 'Create, update or delete syllabus versions',
            },
            {
                'slug': 'read_event',
                'description': 'List and retrieve event information',
            },
            {
                'slug': 'crud_event',
                'description': 'Create, update or delete event information',
            },
            {
                'slug':
                'read_cohort',
                'description':
                'List all the cohorts or a single cohort information',
            },
            {
                'slug': 'crud_cohort',
                'description': 'Create, update or delete cohort info',
            },
            {
                'slug': 'read_eventcheckin',
                'description': 'List and read all the event_checkins',
            },
            {
                'slug': 'read_survey',
                'description': 'List all the nps answers',
            },
            {
                'slug': 'crud_survey',
                'description': 'Create, update or delete surveys',
            },
            {
                'slug': 'read_nps_answers',
                'description': 'List all the nps answers',
            },
            {
                'slug': 'read_lead',
                'description': 'List all the leads',
            },
            {
                'slug': 'crud_lead',
                'description': 'Create, update or delete academy leads',
            },
            {
                'slug': 'read_media',
                'description': 'List all the medias',
            },
            {
                'slug': 'crud_media',
                'description': 'Create, update or delete academy medias',
            },
            {
                'slug': 'read_media_resolution',
                'description': 'List all the medias resolutions',
            },
            {
                'slug':
                'crud_media_resolution',
                'description':
                'Create, update or delete academy media resolutions',
            },
            {
                'slug':
                'read_cohort_activity',
                'description':
                'Read low level activity in a cohort (attendancy, etc.)',
            },
            {
                'slug': 'generate_academy_token',
                'description':
                'Create a new token only to be used by the academy',
            },
            {
                'slug': 'get_academy_token',
                'description': 'Read the academy token',
            },
            {
                'slug':
                'send_reset_password',
                'description':
                'Generate a temporal token and resend forgot password link',
            },
            {
                "slug": "read_activity",
                "description": "List all the user activities"
            },
            {
                "slug": "crud_activity",
                "description": "Create, update or delete a user activities"
            },
            {
                "slug": "read_assigment",
                "description": "List all the assigments"
            },
            {
                "slug": "crud_assigment",
                "description": "Create, update or delete a assigment"
            },
        ])
