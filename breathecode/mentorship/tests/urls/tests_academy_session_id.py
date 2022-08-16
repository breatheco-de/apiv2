"""
This file just can contains duck tests refert to AcademyInviteView
"""
from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import MentorshipTestCase
from django.utils import timezone

UTC_NOW = timezone.now()


def format_datetime(self, date):
    if date is None:
        return None

    return self.bc.datetime.to_iso_string(date)


def get_serializer(self, mentorship_session, mentor_profile, mentorship_service, user, data={}):
    return {
        'accounted_duration': mentorship_session.accounted_duration,
        'agenda': mentorship_session.agenda,
        'bill': mentorship_session.bill,
        'allow_billing': mentorship_session.allow_billing,
        'starts_at': format_datetime(self, mentorship_session.starts_at),
        'ends_at': format_datetime(self, mentorship_session.ends_at),
        'started_at': format_datetime(self, mentorship_session.started_at),
        'ended_at': format_datetime(self, mentorship_session.ended_at),
        'id': mentorship_session.id,
        'mentee': user.id,
        'service': mentorship_service.id,
        'mentee_left_at': mentorship_session.mentee_left_at,
        'mentor': mentor_profile.id,
        'is_online': mentorship_session.is_online,
        'latitude': mentorship_session.latitude,
        'longitude': mentorship_session.longitude,
        'mentor_joined_at': mentorship_session.mentor_joined_at,
        'mentor_left_at': mentorship_session.mentor_left_at,
        'status': mentorship_session.status,
        'summary': mentorship_session.summary,
        'name': mentorship_session.name,
        'online_meeting_url': mentorship_session.online_meeting_url,
        'online_recording_url': mentorship_session.online_recording_url,
        **data,
    }


class AcademyServiceTestSuite(MentorshipTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test__get__without_auth(self):
        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': 'Authentication credentials were not provided.',
            'status_code': status.HTTP_401_UNAUTHORIZED,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__get__without_academy_header(self):
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "Missing academy_id parameter expected for the endpoint url or 'Academy' header",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET capability
    """

    def test__get__without_capabilities(self):
        model = self.bc.database.create(user=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: read_mentorship_session for academy 1",
            'status_code': 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    """
    🔽🔽🔽 GET without data
    """

    def test__get__without_data(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    """
    🔽🔽🔽 GET with one MentorshipSession, MentorProfile and MentorshipService
    """

    def test__get__with_one_mentor_profile(self):
        model = self.bc.database.create(user=1,
                                        role=1,
                                        capability='read_mentorship_session',
                                        mentorship_session=1,
                                        mentor_profile=1,
                                        mentorship_service=1,
                                        profile_academy=1)

        self.bc.request.set_headers(academy=1)
        self.bc.request.authenticate(model.user)

        url = reverse_lazy('mentorship:academy_session_id', kwargs={'session_id': 1})
        response = self.client.get(url)

        json = response.json()
        expected = get_serializer(self,
                                  model.mentorship_session,
                                  model.mentor_profile,
                                  model.mentorship_service,
                                  model.user,
                                  data={})

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('mentorship.MentorshipSession'), [
            self.bc.format.to_dict(model.mentorship_session),
        ])
