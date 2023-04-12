from datetime import datetime, timedelta
import os
import random
from unittest.mock import MagicMock, call, patch
from breathecode.events.caches import EventCache
from django.urls.base import reverse_lazy
from django.template import loader

from breathecode.utils.api_view_extensions.api_view_extension_handlers import APIViewExtensionHandlers
from ..mixins.new_events_tests_case import EventTestCase
from django.utils import timezone

UTC_NOW = timezone.now()


def consumption_session(event, event_type_set, user, consumable, data={}):
    return {
        'consumable_id': consumable.id,
        'duration': timedelta(),
        'eta': ...,
        'how_many': 1.0,
        'id': 0,
        'path': 'payments.EventTypeSet',
        'related_id': event_type_set.id,
        'related_slug': event_type_set.slug,
        'request': {
            'args': [],
            'headers': {
                'academy': None
            },
            'kwargs': {
                'event_id': event.id,
            },
            'user': user.id
        },
        'status': 'PENDING',
        'user_id': user.id,
        'was_discounted': False,
        **data,
    }


def event_checkin_serializer(id, event, user):
    return {
        'attended_at': UTC_NOW,
        'attendee_id': user.id,
        'email': user.email,
        'event_id': event.id,
        'id': id,
        'status': 'DONE',
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_message(message):
    request = None
    context = {'MESSAGE': message, 'BUTTON': None, 'BUTTON_TARGET': '_blank', 'LINK': None}

    return loader.render_to_string('message.html', context, request)


def serializer(event):
    return {
        'id': event.id,
        'starting_at': event.starting_at,
        'ending_at': event.ending_at,
        'live_stream_url': event.live_stream_url,
        'title': event.title,
    }


# IMPORTANT: the loader.render_to_string in a function is inside of function render
def render_countdown(event, token):
    request = None
    context = {
        'event': serializer(event),
        'token': token.key,
    }

    return loader.render_to_string('countdown.html', context, request)


class AcademyEventTestSuite(EventTestCase):
    cache = EventCache()

    # When: no auth
    # Then: return 401
    def test_no_auth(self):

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': 1})

        response = self.client.get(url)

        url_hash = self.bc.format.to_base64('/v1/events/me/event/1/join')
        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/v1/auth/view/login?attempt=1&url={url_hash}')

    # When: no consumables
    # Then: return 402
    def test_no_consumables(self):
        model = self.bc.database.create(user=1, token=1)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': 1}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('not-enough-consumables')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 402)

        self.assertEqual(self.bc.database.list_of('events.Event'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: no Consumable, Event, EventTypeSet, and IOweYou, User have Group and Permission
    # When: Feature flag set to False
    # Then: return 404
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=False))
    def test_no_consumables__bypass_with_feature_flag__live_event_not_found(self):
        permission = {'codename': 'event_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission, token=1)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': 1}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('not-found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of('events.Event'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: no Consumable, with Event, EventTypeSet, IOweYou, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and event.live_stream_url not set
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=False))
    def test_no_consumables__bypass_with_feature_flag__with_live_event__cohort_without_url(self):
        permission = {'codename': 'event_join'}
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {'starting_at': UTC_NOW - delta, 'ending_at': UTC_NOW + delta}
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('event-online-meeting-url-not-found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: no Consumable, with Event, EventTypeSet, IOweYou, CohortUser, User have Group and Permission
    # When: Feature flag set to False, right hash and event.live_stream_url set
    # Then: return 301 to cohort.online_meeting_url and create a EventCheckin with status DONE
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=False))
    def test_no_consumables__bypass_with_feature_flag__with_live_event__cohort_with_url(self):
        permission = {'codename': 'event_join'}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            'starting_at': UTC_NOW - delta,
            'ending_at': UTC_NOW + delta,
            'live_stream_url': online_meeting_url,
        }
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, online_meeting_url)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [
            event_checkin_serializer(1, model.event, model.user),
        ])

    # Given: no Consumable and Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True
    # Then: return 404
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_no_consumables__it_try_to_consume__live_event_not_found(self):
        permission = {'codename': 'event_join'}
        model = self.bc.database.create(user=1, group=1, permission=permission, token=1)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': 1}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('not-found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(self.bc.database.list_of('events.Event'), [])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: no Consumable with Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event.live_stream_url not set
    # Then: return 400
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_no_consumables__it_try_to_consume__with_live_event__cohort_without_url(self):
        permission = {'codename': 'event_join'}
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {'starting_at': UTC_NOW - delta, 'ending_at': UTC_NOW + delta}
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('event-online-meeting-url-not-found')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: no Consumable with Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event.live_stream_url set
    # Then: return 402
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_no_consumables__it_try_to_consume__with_live_event__cohort_with_url(self):
        permission = {'codename': 'event_join'}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            'starting_at': UTC_NOW - delta,
            'ending_at': UTC_NOW + delta,
            'live_stream_url': online_meeting_url,
        }
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('with-consumer-not-enough-consumables')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 402)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [])
        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True, event end in the past and event.live_stream_url set
    # Then: return 200 and create a ConsumptionSession
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_past(self):
        permission = {'codename': 'event_join'}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            'starting_at': UTC_NOW - delta,
            'ending_at': UTC_NOW - delta,
            'live_stream_url': online_meeting_url,
        }
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        consumable=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_message('event-has-ended')

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event end in the future
    # Then: return 200 and create a ConsumptionSession and create a EventCheckin with status DONE
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future(self):
        permission = {'codename': 'event_join'}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            'starting_at': UTC_NOW - delta,
            'ending_at': UTC_NOW + delta,
            'live_stream_url': online_meeting_url,
        }
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        consumable=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = ''

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, online_meeting_url)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            consumption_session(model.event,
                                model.event_type_set,
                                model.user,
                                model.consumable,
                                data={
                                    'id': 1,
                                    'duration': delta,
                                    'eta': UTC_NOW + delta,
                                }),
        ])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [
            event_checkin_serializer(1, model.event, model.user),
        ])

    # Given: with Consumable, Event, EventTypeSet, IOweYou, User have Group and Permission
    # When: Feature flag set to True and event start and end in the future
    # Then: return 200 and create a ConsumptionSession
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    @patch('breathecode.events.permissions.flags.Release.enable_consume_live_events',
           MagicMock(return_value=True))
    def test_with_consumable__it_try_to_consume__with_live_event__in_the_future__show_countdown(self):
        permission = {'codename': 'event_join'}
        online_meeting_url = self.bc.fake.url()
        delta = timedelta(seconds=random.randint(1, 1000))
        event = {
            'starting_at': UTC_NOW + delta,
            'ending_at': UTC_NOW + delta,
            'live_stream_url': online_meeting_url,
        }
        event_type = {'icon_url': self.bc.fake.url()}

        is_subscription = bool(random.randbytes(1))
        i_owe_you = {
            'next_payment_at': UTC_NOW + timedelta(weeks=4),
            'valid_until': UTC_NOW + timedelta(weeks=4),
        }

        if is_subscription and bool(random.randbytes(1)):
            i_owe_you['valid_until'] = None

        extra = {'subscription' if is_subscription else 'plan_financing': i_owe_you}
        model = self.bc.database.create(user=1,
                                        group=1,
                                        permission=permission,
                                        event=event,
                                        event_type=event_type,
                                        event_type_set=1,
                                        consumable=1,
                                        token=1,
                                        **extra)
        querystring = self.bc.format.to_querystring({'token': model.token.key})

        url = reverse_lazy('events:me_event_id_join', kwargs={'event_id': model.event.id}) + f'?{querystring}'

        response = self.client.get(url)

        content = self.bc.format.from_bytes(response.content)
        expected = render_countdown(model.event, model.token)

        # dump error in external files
        if content != expected:
            with open('content.html', 'w') as f:
                f.write(content)

            with open('expected.html', 'w') as f:
                f.write(expected)

        self.assertEqual(content, expected)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.bc.database.list_of('events.Event'), [
            self.bc.format.to_dict(model.event),
        ])
        self.assertEqual(self.bc.database.list_of('payments.Consumable'), [
            self.bc.format.to_dict(model.consumable),
        ])

        self.assertEqual(self.bc.database.list_of('payments.ConsumptionSession'), [
            consumption_session(model.event,
                                model.event_type_set,
                                model.user,
                                model.consumable,
                                data={
                                    'id': 1,
                                    'duration': delta,
                                    'eta': UTC_NOW + delta,
                                }),
        ])
        self.assertEqual(self.bc.database.list_of('events.EventCheckin'), [])
