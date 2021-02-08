"""
Collections of mixins used to login in authorize microservice
"""
import os
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer

class EventsModelsMixin(ModelsMixin):
    def generate_events_models(self, organization=False, user=False,
            organizer=False, academy=False, venue=False, event_type=False,
            event=False, event_checkin=False, eventbrite_webhook=False,
            models={}, **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'organization' in models or organization:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['organization'] = mixer.blend('events.Organization', **kargs)

        if not 'organizer' in models or organizer:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            models['organizer'] = mixer.blend('events.Organizer', **kargs)

        if not 'venue' in models or venue:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            models['venue'] = mixer.blend('events.Venue', **kargs)

        if not 'event_type' in models or event_type:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['event_type'] = mixer.blend('events.EventType', **kargs)

        if not 'event' in models or event:
            kargs = {}

            if 'user' in models or user:
                kargs['host'] = models['user']

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            if 'user' in models or user:
                kargs['author'] = models['user']

            if 'venue' in models or venue:
                kargs['venue'] = models['venue']

            if 'event_type' in models or event_type:
                kargs['event_type'] = models['event_type']

            models['event'] = mixer.blend('events.Event', **kargs)

        if not 'event_checkin' in models or event_checkin:
            kargs = {}

            if 'user' in models or user:
                kargs['attendee'] = models['user']

            if 'event' in models or event:
                kargs['event'] = models['event']

            models['event_checkin'] = mixer.blend('events.EventCheckin', **kargs)

        if not 'eventbrite_webhook' in models or eventbrite_webhook:
            models['eventbrite_webhook'] = mixer.blend('events.EventbriteWebhook')

        return models
