"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.events.models import EventbriteWebhook, Organization, EventCheckin
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

    def headers(self, event='test'):
        return {
            'X-Eventbrite-Event': event,
            'Accept': 'text/plain',
            'User-Agent': 'Eventbrite Hookshot 12345c6',
            'X-Eventbrite-Delivery': '1234567',
            'Content-type': 'application/json',
            'User-ID-Sender': '123456789012',
        }

    def data(self, action='test', url='https://www.eventbriteapi.com/v3/test'):
        return {
            'api_url': url,
            'config': {
                'user_id': '123456789012',
                'action': action,
                'webhook_id': '1234567',
                'endpoint_url': 'https://something.io/eventbrite/webhook'
            }
        }

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

    def all_event_checkin_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            EventCheckin.objects.filter()]

    def all_eventbrite_webhook_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in
            EventbriteWebhook.objects.filter()]

    def generate_models(self, language='', user=False, organization=False, academy=False,
            organizer=False, venue=False, event_type=False, event=False, event_checkin=False,
            event_ticket=False, authenticate=False, active_campaign_academy=False, in_miami=False,
            eventbrite_event_id=0, attendee=False, automation=False,
            with_event_attendancy_automation=False, models={}):
        """Generate models"""
        self.maxDiff = None
        models = models.copy()

        if not 'user' in models and (user or event or event_checkin or event_ticket or
                authenticate):
            models['user'] = mixer.blend('auth.User')

        if not 'attendee' in models and attendee:
            kargs = {
                'email': 'jhon.smith@example.com',
                'first_name': 'John',
                'last_name': 'Smith',
            }
            models['attendee'] = mixer.blend('auth.User', **kargs)

        if authenticate:
            self.client.force_authenticate(user=models['user'])

        if not 'academy' in models and (academy or organization or venue or event_type or event or
                event_checkin or event_ticket or active_campaign_academy or in_miami):
            kargs = {}

            if in_miami:
                kargs['name'] = '4Geeks Academy Miami'
                kargs['slug'] = 'downtown-miami'
    
            models['academy'] = mixer.blend('admissions.Academy', **kargs)

        if not 'active_campaign_academy' in models and (active_campaign_academy or automation):
            kargs = {
                'academy': models['academy'],
                'ac_url': 'https://old.hardcoded.breathecode.url',
            }

            models['active_campaign_academy'] = mixer.blend('marketing.ActiveCampaignAcademy', **kargs)

        if not 'automation' in models and automation:
            kargs = {
                'status': '1',
                'name': 'Workshop Attendancy',
                'ac_academy': models['active_campaign_academy'],
            }

            models['automation'] = mixer.blend('marketing.Automation', **kargs)

        # cannot move it into active_campaign_academy scope because one circular reference
        if with_event_attendancy_automation:
            models['active_campaign_academy'].event_attendancy_automation = models['automation']
            models['active_campaign_academy'].save()

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

            if eventbrite_event_id:
                kargs['eventbrite_id'] = eventbrite_event_id

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
