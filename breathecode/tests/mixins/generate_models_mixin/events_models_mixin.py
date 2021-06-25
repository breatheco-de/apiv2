"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class EventsModelsMixin(ModelsMixin):
    def generate_events_models(self,
                               organization=False,
                               user=False,
                               organizer=False,
                               academy=False,
                               venue=False,
                               event_type=False,
                               event=False,
                               event_checkin=False,
                               eventbrite_webhook=False,
                               organization_kwargs={},
                               organizer_kwargs={},
                               venue_kwargs={},
                               event_type_kwargs={},
                               event_kwargs={},
                               event_checkin_kwargs={},
                               eventbrite_webhook_kwargs={},
                               models={},
                               **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'organization' in models and organization:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **organization_kwargs}
            models['organization'] = mixer.blend('events.Organization',
                                                 **kargs)

        if not 'organizer' in models or organizer:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            kargs = {**kargs, **organizer_kwargs}
            models['organizer'] = mixer.blend('events.Organizer', **kargs)

        if not 'venue' in models and venue:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            kargs = {**kargs, **venue_kwargs}
            models['venue'] = mixer.blend('events.Venue', **kargs)

        if not 'event_type' in models and event_type:
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **event_type_kwargs}
            models['event_type'] = mixer.blend('events.EventType', **kargs)

        if not 'event' in models and event:
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

            kargs = {**kargs, **event_kwargs}
            models['event'] = mixer.blend('events.Event', **kargs)

        if not 'event_checkin' in models and event_checkin:
            kargs = {}

            if 'user' in models or user:
                kargs['attendee'] = models['user']

            if 'event' in models or event:
                kargs['event'] = models['event']

            kargs = {**kargs, **event_checkin_kwargs}
            models['event_checkin'] = mixer.blend('events.EventCheckin',
                                                  **kargs)

        if not 'eventbrite_webhook' in models and eventbrite_webhook:
            kargs = {}

            kargs = {**kargs, **eventbrite_webhook_kwargs}
            models['eventbrite_webhook'] = mixer.blend(
                'events.EventbriteWebhook', **kargs)

        return models
