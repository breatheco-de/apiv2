import logging
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.db.models import Q

logger = logging.getLogger(__name__)

# {
#   "cancel_url": "https://calendly.com/cancellations/AAAAAAAAAAAAAAAA",
#   "created_at": "2020-11-23T17:51:18.327602Z",
#   "email": "test@example.com",
#   "event": "https://api.calendly.com/scheduled_events/AAAAAAAAAAAAAAAA",
#   "first_name": "John",
#   "last_name": "Doe",
#   "name": "John Doe",
#   "new_invitee": null,
#   "old_invitee": null,
#   "questions_and_answers": [],
#   "reschedule_url": "https://calendly.com/reschedulings/AAAAAAAAAAAAAAAA",
#   "rescheduled": false,
#   "status": "active",
#   "text_reminder_number": null,
#   "timezone": "America/New_York",
#   "tracking": {
#     "utm_campaign": null,
#     "utm_source": null,
#     "utm_medium": null,
#     "utm_content": null,
#     "utm_term": null,
#     "salesforce_uuid": null
#   },
#   "updated_at": "2020-11-23T17:51:18.341657Z",
#   "uri": "https://api.calendly.com/scheduled_events/AAAAAAAAAAAAAAAA/invitees/AAAAAAAAAAAAAAAA",
#   "canceled": false,
#   "routing_form_submission": "https://api.calendly.com/routing_form_submissions/AAAAAAAAAAAAAAAA",
#   "payment": {
#     "external_id": "ch_AAAAAAAAAAAAAAAAAAAAAAAA",
#     "provider": "stripe",
#     "amount": 1234.56,
#     "currency": "USD",
#     "terms": "sample terms of payment (up to 1,024 characters)",
#     "successful": true
#   },
#   "no_show": {
#     "uri": "https://api.calendly.com/invitee_no_shows/6ee96ed4-83a3-4966-a278-cd19b3c02e09",
#     "created_at": "2020-11-23T17:51:18.341657Z"
#   },
#   "reconfirmation": {
#     "created_at": "2020-11-23T17:51:18.341657Z",
#     "confirmed_at": "2020-11-23T20:01:18.341657Z"
#   },
#   "scheduling_method": null,
#   "invitee_scheduled_by": null,
#   "scheduled_event": {
#     "uri": "https://api.calendly.com/scheduled_events/GBGBDCAADAEDCRZ2",
#     "name": "15 Minute Meeting",
#     "meeting_notes_plain": "Internal meeting notes",
#     "meeting_notes_html": "<p>Internal meeting notes</p>",
#     "status": "active",
#     "start_time": "2019-08-24T14:15:22.123456Z",
#     "end_time": "2019-08-24T14:15:22.123456Z",
#     "event_type": "https://api.calendly.com/event_types/GBGBDCAADAEDCRZ2",
#     "location": {
#       "type": "physical",
#       "location": "string",
#       "additional_info": "string"
#     },
#     "invitees_counter": {
#       "total": 0,
#       "active": 0,
#       "limit": 0
#     },
#     "created_at": "2019-01-02T03:04:05.678123Z",
#     "updated_at": "2019-01-02T03:04:05.678123Z",
#     "event_memberships": [
#       {
#         "user": "https://api.calendly.com/users/GBGBDCAADAEDCRZ2",
#         "user_email": "user@example.com",
#         "user_name": "John Smith"
#       }
#     ],
#     "event_guests": [
#       {
#         "email": "user@example.com",
#         "created_at": "2019-08-24T14:15:22.123456Z",
#         "updated_at": "2019-08-24T14:15:22.123456Z"
#       }
#     ]
#   }
# }


def invitee_created(client, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.mentorship.models import MentorProfile, MentorshipService, MentorshipSession
    from breathecode.mentorship.tasks import create_room_on_google_meet

    # from breathecode.events.actions import update_or_create_event
    # payload = payload['resource']

    academy = webhook.organization.academy

    service = None
    service_slug = payload['tracking']['utm_campaign']
    if service_slug is None:
        raise Exception('Missing service information on calendly iframe info: tracking->utm_campaign')

    service = MentorshipService.objects.filter(slug=service_slug, academy=academy).first()
    if service is None:
        raise Exception(f'Service with slug {service_slug} not found for academy {academy.name}')

    mentee = None
    mentee_id = 'undefined'
    if 'salesforce_uuid' in payload['tracking'] and payload['tracking']['salesforce_uuid'] != '':
        mentee_id = payload['tracking']['salesforce_uuid']
        mentee = User.objects.filter(id=mentee_id).first()

    if mentee is None:
        mentee_email = payload['email']
        mentee = User.objects.filter(email=mentee_email).first()

    if mentee is None:
        raise Exception(f'Mentee user not found with email {mentee_email} or id {mentee_id}')

    event_uuid = urlparse(payload['event']).path.split('/')[-1]
    event = client.get_event(event_uuid)
    if event is None or 'resource' not in event:
        raise Exception(f'Event with uuid {event_uuid} not found on calendly')
    event = event['resource']

    if not isinstance(event['event_memberships'], list) or len(event['event_memberships']) == 0:
        raise Exception('No mentor information was found on calendly event')

    mentor_email = event['event_memberships'][0]['user_email']
    mentor_uuid = urlparse(event['event_memberships'][0]['user']).path.split('/')[-1]

    mentor = MentorProfile.objects.filter(
        academy=academy).filter(Q(calendly_uuid=mentor_uuid) | Q(email=mentor_email)
                                | Q(user__email=mentor_email)).first()
    if mentor is None:
        raise Exception(f'Mentor not found with uuid {mentor_uuid} and email {mentor_email}')

    if mentor.status in ['INVITED', 'INNACTIVE']:
        raise Exception(f'Mentor status is {mentor.status}')

    if mentor.services.filter(slug=service.slug).first() is None:
        raise Exception(f'Mentor {mentor.name} is not assigned for service {service.slug}')

    meeting_url = None
    if 'location' in payload and 'join_url' in payload['location']:
        meeting_url = payload['location']['join_url']

    session = MentorshipSession.objects.filter(calendly_uuid=event_uuid).first()
    if session is None:
        session = MentorshipSession()

    session.is_online = True
    session.mentor = mentor
    session.mentee = mentee
    session.online_meeting_url = meeting_url
    session.status_message = 'Scheduled throught calendly'
    session.starts_at = event['start_time']
    session.ends_at = event['end_time']
    session.service = service
    session.calendly_uuid = event_uuid
    session.save()

    if session.service and session.service.video_provider == MentorshipService.VideoProvider.GOOGLE_MEET:
        create_room_on_google_meet.delay(session.id)

    return session
