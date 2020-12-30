"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.events.models import Organization
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from .development_environment import DevelopmentEnvironment
# from ...models import Certificate, Cohort
# from ..mocks import (
#     GOOGLE_CLOUD_PATH,
#     apply_google_cloud_client_mock,
#     apply_google_cloud_bucket_mock,
#     apply_google_cloud_blob_mock
# )

class EventTestCase(APITestCase, DevelopmentEnvironment):
    """APITestCase with Event models"""

    def remove_model_state(self, dict):
        result = None
        if dict:
            result = dict.copy()
            del result['_state']
        return result

    def remove_created_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'created_at' in result:
                del result['created_at']
        return result

    def remove_updated_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if 'updated_at' in result:
                del result['updated_at']
        return result

    def remove_dinamics_fields(self, dict):
        return self.remove_updated_at(self.remove_model_state(self.remove_created_at(dict)))

    def model_to_dict(self, models: dict, key: str) -> dict:
        if key in models:
            return self.remove_dinamics_fields(models[key].__dict__)

    def all_organization_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            Organization.objects.filter()]

    def generate_models(self, language='', user=False, organization=False, academy=False,
            organizer=False, venue=False, event_type=False, event=False, event_checkin=False,
            event_ticket=False, models={}):
        """Generate models"""
        self.maxDiff = None
        models = models.copy()

        if not 'user' in models and (user or event or event_checkin or event_ticket):
            models['user'] = mixer.blend('auth.User')

        if not 'academy' in models and (academy or organization or venue or event_type or event or
                event_checkin or event_ticket):
            models['academy'] = mixer.blend('admissions.Academy')

        if not 'organization' in models and (organization or organizer or venue or event or
                event_checkin or event_ticket):
            kargs = {
                'academy': models['academy']
            }

            models['organization'] = mixer.blend('events.Organization', **kargs)

        if not 'organizer' in models and organizer:
            kargs = {
                'academy': models['academy'],
                'organization': models['organization'],
            }

            models['organizer'] = mixer.blend('events.Organizer', **kargs)

        if not 'venue' in models and (venue or event or event_checkin or event_ticket):
            kargs = {
                'academy': models['academy'],
                'organization': models['organization'],
            }

            models['venue'] = mixer.blend('events.Venue', **kargs)

        if not 'event_type' in models and (event_type or event or event_checkin or event_ticket):
            kargs = {
                'academy': models['academy']
            }

            models['event_type'] = mixer.blend('events.EventType', **kargs)

        if not 'host_user' in models and (event or event_checkin or event_ticket):
            models['host_user'] = mixer.blend('auth.User')

        if not 'event' in models and (event or event_checkin or event_ticket):
            kargs = {
                'host': models['host_user'],
                'academy': models['academy'],
                'organization': models['organization'],
                'author': models['user'],
                'venue': models['venue'],
                'event_type': models['event_type'],
            }

            if language:
                kargs['lang'] = language

            models['event'] = mixer.blend('events.Event', **kargs)

        if not 'event_checkin' in models and event_checkin:
            kargs = {
                'attendee': models['user'],
                'event': models['event'],
            }

            models['event_checkin'] = mixer.blend('events.EventCheckin', **kargs)

        if not 'event_ticket' in models and event_ticket:
            kargs = {
                'attendee': models['user'],
                'event': models['event'],
            }

            models['event_ticket'] = mixer.blend('events.EventTicket', **kargs)

        return models
