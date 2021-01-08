

def placed(self, payload: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.marketing.actions import add_to_active_campaign
    from breathecode.events.models import EventCheckin

    # wonderful way to fix one poor mocking system
    import requests

    if not 'email' in payload:
        pass

    from pprint import pprint
    print('adssadasdsadsad', payload)
    pprint(payload)

    event_id = payload['event_id']

    # get attendee
    url = f'https://www.eventbriteapi.com/v3/events/{event_id}/attendees/'
    response = requests.get(url, headers=self.headers)
    json = response.json()
    attendee = json["attendees"][0]

    # get event
    url = f'https://www.eventbriteapi.com/v3/events/{event_id}/'
    response = requests.get(url, headers=self.headers)
    json = response.json()
    attendee = json["attendees"][0]

    # try:
    #     ticket = EventCheckin(
    #         email=payload['email'],
    #         status='PENDING',
    #         # event
    #         # attendee
    #     )
    #     ticket.save()
    # except Exception as e:
    #     print(str(e))

    aaa = {
        'email': payload['email'],
        'first_name': payload['first_name'],
        'last_name': payload['last_name'],
        # 'name': payload['name'],
    }

    add_to_active_campaign()
