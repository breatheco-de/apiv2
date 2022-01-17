"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models


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

        if not 'organization' in models and is_valid(organization):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['organization'] = create_models(organization, 'events.Organization', **{
                **kargs,
                **organization_kwargs
            })

        if not 'organizer' in models and is_valid(organizer):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            models['organizer'] = create_models(organizer, 'events.Organizer', **{
                **kargs,
                **organizer_kwargs
            })

        if not 'venue' in models and is_valid(venue):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            if 'organization' in models or organization:
                kargs['organization'] = models['organization']

            models['venue'] = create_models(venue, 'events.Venue', **{**kargs, **venue_kwargs})

        if not 'event_type' in models and is_valid(event_type):
            kargs = {}

            if 'academy' in models or academy:
                kargs['academy'] = models['academy']

            models['event_type'] = create_models(event_type, 'events.EventType', **{
                **kargs,
                **event_type_kwargs
            })

        if not 'event' in models and is_valid(event):
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

            models['event'] = create_models(event, 'events.Event', **{**kargs, **event_kwargs})

        if not 'event_checkin' in models and is_valid(event_checkin):
            kargs = {}

            if 'user' in models or user:
                kargs['attendee'] = models['user']

            if 'event' in models or event:
                kargs['event'] = models['event']

            models['event_checkin'] = create_models(event_checkin, 'events.EventCheckin', **{
                **kargs,
                **event_checkin_kwargs
            })

        if not 'eventbrite_webhook' in models and is_valid(eventbrite_webhook):
            kargs = {}

            models['eventbrite_webhook'] = create_models(eventbrite_webhook, 'events.EventbriteWebhook', **{
                **kargs,
                **eventbrite_webhook_kwargs
            })

        return models
