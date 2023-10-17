from breathecode.utils import Cache
from .models import Event, LiveClass


class EventCache(Cache):
    model = Event
    depends = ['User', 'Academy', 'Organization', 'Venue', 'EventType']
    parents = ['EventCheckin', 'EventbriteWebhook', 'Answer']


class LiveClassCache(Cache):
    model = LiveClass
    depends = ['CohortTimeSlot']
    parents = []
