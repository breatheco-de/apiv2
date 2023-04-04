from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy

from ..mixins.new_events_tests_case import EventTestCase

from breathecode.utils.api_view_extensions.extensions import lookup_extension


def get_serializer(self, event_type, data={}):
    ended_at = event_type.ended_at
    if ended_at:
        ended_at = self.bc.datetime.to_iso_string(event_type.ending_at)

    started_at = event_type.started_at
    if started_at:
        started_at = self.bc.datetime.to_iso_string(event_type.started_at)

    return {
        'id': event_type.id,
        'started_at': started_at,
        'ended_at': ended_at,
        'starting_at': self.bc.datetime.to_iso_string(event_type.starting_at),
        'ending_at': self.bc.datetime.to_iso_string(event_type.ending_at),
        'hash': event_type.hash,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):

    # When: I call the API without authentication
    # Then: I should get a 401 error
    def test_no_auth(self):
        url = reverse_lazy('events:academy_event_liveclass')

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    # Given: User
    # When: User is authenticated and has no LiveClass
    # Then: I should get a 200 status code with no data
    def test_zero_live_classes(self):
        model = self.bc.database.create(user=1, profile_academy=1, role=1, capability='start_or_end_class')

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('events:academy_event_liveclass')

        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])

    # Given: a User, LiveClass, Cohort and CohortTimeSlot
    # When: User is authenticated, has LiveClass and CohortUser belongs to this LiveClass
    # Then: I should get a 200 status code with the LiveClass data
    def test_one_live_class(self):
        model = self.bc.database.create(user=1,
                                        live_class=1,
                                        cohort=1,
                                        cohort_time_slot=1,
                                        cohort_user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='start_or_end_class')

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)
        url = reverse_lazy('events:academy_event_liveclass')

        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(self, model.live_class)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])

    # Given: LiveClass.objects.filter is mocked
    # When: the mock is called
    # Then: the mock should be called with the correct arguments and does not raise an exception
    @patch('breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup',
           MagicMock(wraps=lookup_extension.compile_lookup))
    def test_lookup_extension(self):
        model = self.bc.database.create(user=1,
                                        live_class=1,
                                        cohort=1,
                                        cohort_time_slot=1,
                                        cohort_user=1,
                                        profile_academy=1,
                                        role=1,
                                        capability='start_or_end_class')

        self.bc.request.authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        args, kwargs = self.bc.format.call(
            self.bc.database.get_model('events.LiveClass'),
            'en',
            fields={
                'exact': [
                    'remote_meeting_url',
                    'cohort_time_slot__cohort__cohortuser__user',
                    'cohort_time_slot__cohort__cohortuser__user__email',
                ],
                'gte': ['starting_at'],
                'lte': ['ending_at'],
                'id': [
                    'cohort_time_slot__cohort',
                    'cohort_time_slot__cohort__academy',
                    'cohort_time_slot__cohort__syllabus_version__syllabus',
                ],
                'is_null': ['ended_at'],
            },
            overwrite={
                'cohort': 'cohort_time_slot__cohort',
                'academy': 'cohort_time_slot__cohort__academy',
                'syllabus': 'cohort_time_slot__cohort__syllabus_version__syllabus',
                'start': 'starting_at',
                'end': 'ending_at',
                'upcoming': 'ended_at',
                'user': 'cohort_time_slot__cohort__cohortuser__user',
                'user_email': 'cohort_time_slot__cohort__cohortuser__user__email',
            },
        )

        query, _ = self.bc.format.lookup(*args, **kwargs)
        url = reverse_lazy('events:academy_event_liveclass') + '?' + self.bc.format.querystring(query)

        self.assertEqual([x for x in query], [
            'remote_meeting_url',
            'upcoming',
            'start',
            'end',
            'academy',
            'syllabus',
            'cohort',
            'user',
            'user_email',
        ])

        response = self.client.get(url)

        json = response.json()
        expected = []

        self.assertEqual(lookup_extension.compile_lookup.call_args_list, [
            call(query, *args, **kwargs, custom_fields={}),
        ])

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])
        assert 0
