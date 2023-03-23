from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from django.utils import timezone


def get_serializer(self, live_class, cohort, data={}):
    ended_at = live_class.ended_at
    if ended_at:
        ended_at = self.bc.datetime.to_iso_string(ended_at)

    ending_at = live_class.ending_at
    if ending_at:
        ending_at = self.bc.datetime.to_iso_string(ending_at)

    started_at = live_class.started_at
    if started_at:
        started_at = self.bc.datetime.to_iso_string(started_at)

    starting_at = live_class.starting_at
    if starting_at:
        starting_at = self.bc.datetime.to_iso_string(starting_at)

    return {
        'ended_at': ended_at,
        'ending_at': ending_at,
        'hash': live_class.hash,
        'id': live_class.id,
        'started_at': started_at,
        'starting_at': starting_at,
        'url': cohort.online_meeting_url,
        **data,
    }


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    # When: no auth
    # Then: return 401
    def test_no_auth(self):

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': 'potato'})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'Authentication credentials were not provided.', 'status_code': 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    # When: no consumables
    # Then: return 402
    def test_no_consumables(self):
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': 'potato'})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'not-enough-consumables', 'status_code': 402}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 402)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: no Consumable and LiveClass, User have Group and Permission
    # When: Feature flag set to False
    # Then: return 404
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_classes',
           MagicMock(return_value=False))
    def test_no_consumables__bypass_with_feature_flag__live_class_not_found(self):
        permission = {'codename': 'live_class_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': 'potato'})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: no Consumable, with LiveClass, CohortUser, User have Group and Permission
    # When: Feature flag set to False and right hash
    # Then: return 200
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_classes',
           MagicMock(return_value=False))
    def test_no_consumables__bypass_with_feature_flag__with_live_class(self):
        permission = {'codename': 'live_class_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission, live_class=1, cohort_user=1)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': model.live_class.hash})

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(self, model.live_class, model.cohort)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: no Consumable and LiveClass, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 404
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_classes',
           MagicMock(return_value=True))
    def test_no_consumables__it_try_to_consume__live_class_not_found(self):
        permission = {'codename': 'live_class_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': 'potato'})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'not-found', 'status_code': 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: no Consumable with LiveClass, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 402
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_classes',
           MagicMock(return_value=True))
    def test_no_consumables__it_try_to_consume__with_live_class(self):
        permission = {'codename': 'live_class_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission, live_class=1, cohort_user=1)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': model.live_class.hash})

        response = self.client.get(url)
        json = response.json()
        expected = {'detail': 'with-consumer-not-enough-consumables', 'status_code': 402}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 402)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])

    # Given: wuth Consumable, LiveClass, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 200
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_classes',
           MagicMock(return_value=True))
    def test_with_consumable__it_try_to_consume__with_live_class(self):
        permission = {'codename': 'live_class_join'}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        live_class=1,
                                        cohort_user=1,
                                        consumable=1)
        self.bc.request.authenticate(user=model.user)

        url = reverse_lazy('events:me_event_liveclass_join_hash', kwargs={'hash': model.live_class.hash})

        response = self.client.get(url)
        json = response.json()
        expected = get_serializer(self, model.live_class, model.cohort)

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [
            self.bc.format.to_dict(model.live_class),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])
