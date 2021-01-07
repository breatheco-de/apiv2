from pprint import pprint
def placed(payload: dict, details: dict):
    # prevent circular dependency import between thousand modules previuosly loaded and cached
    from breathecode.events.models import EventCheckin

    if not 'email' in details:
        pass

    ticket = EventCheckin(
        email=details['email'],
        status='PENDING',
        # event
        # attendee
    )
    ticket.save()

    pprint('payload')
    pprint(payload)
    pprint(details)
