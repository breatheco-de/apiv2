from breathecode.events.models import Event
from breathecode.events.serializers import EventSerializer
from breathecode.utils import ScriptNotification
from django.utils import timezone
from breathecode.utils.datetime_interger import duration_to_str, from_now

published_without_live_stream_url = Event.objects.filter(status='ACTIVE',
                                                         online_event=True,
                                                         live_stream_url='',
                                                         ending_at__gt=timezone.now())
total = published_without_live_stream_url.count()

if total > 0:
    msg = ''
    for event in published_without_live_stream_url:
        msg += f'- <a href="{ADMIN_URL}/events/event/{event.id}">{event.title}</a> added {from_now(event.created_at)} ago. \n'

        event.status = 'draft'
        serializer = EventSerializer(data=event, context={'academy_id': None})
        if serializer.is_valid():
            serializer.save()
        else:
            print(f'The event {event.title} status was not able to be changed.', serializer.errors)

    raise ScriptNotification(f'There are {total} published online events without live stream URL \n\n' + msg,
                             status='CRITICAL',
                             title=f'There are {total} online events published without live stream URL',
                             slug='online-events-without-live-stream-url',
                             btn_url=ADMIN_URL + '/events/list')

print(f'There are no online events without live stream URL')
