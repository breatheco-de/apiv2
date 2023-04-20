from unittest.mock import MagicMock, patch
from django.urls.base import reverse_lazy
from ..mixins.new_events_tests_case import EventTestCase


class AcademyVenueTestSuite(EventTestCase):

    # When: no auth
    # Then: return 401
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_no_auth(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_liveclass_join_hash', kwargs={'hash': '1234'})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    # When: no capability
    # Then: return 403
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_with_no_capability(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_liveclass_join_hash', kwargs={'hash': '1234'})
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = {
            'detail': "You (user: 1) don't have this capability: start_or_end_class for academy 1",
            'status_code': 403
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    # When: no LiveClass
    # Then: return 404
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_no_live_classes(self):
        self.headers(academy=1)
        url = reverse_lazy('events:academy_event_liveclass_join_hash', kwargs={'hash': '1234'})
        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        capability='start_or_end_class',
                                        role='potato')

        self.bc.request.authenticate(model.user)

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    # When: have a LiveClass
    # Then: redirect to the liveclass
    @patch('django.db.models.signals.pre_delete.send', MagicMock(return_value=None))
    @patch('breathecode.admissions.signals.student_edu_status_updated.send', MagicMock(return_value=None))
    def test_a_live_class(self):
        self.headers(academy=1)
        cohort = {'online_meeting_url': self.bc.fake.url()}
        model = self.bc.database.create(user=1,
                                        profile_academy=1,
                                        capability='start_or_end_class',
                                        role='potato',
                                        live_class=1,
                                        cohort=cohort,
                                        cohort_user=1)

        self.bc.request.authenticate(model.user)
        url = reverse_lazy('events:academy_event_liveclass_join_hash', kwargs={'hash': model.live_class.hash})

        response = self.client.get(url)
        expected = b''

        self.assertEqual(response.content, expected)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, model.cohort.online_meeting_url)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])
