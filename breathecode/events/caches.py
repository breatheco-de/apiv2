from breathecode.utils import Cache


class EventCache(Cache):
    model = 'Event'
    depends = ['User', 'Academy', 'Organization', 'Venue', 'EventType']
    parents = ['EventCheckin']
