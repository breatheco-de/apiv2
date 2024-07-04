import logging

from django.db.models import Q
from urllib.parse import urlparse
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def invitee_created(client, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.mentorship.models import MentorshipService, MentorProfile, MentorshipSession

    # from breathecode.events.actions import update_or_create_event
    # payload = payload['resource']

    academy = webhook.organization.academy

    service = None
    service_slug = payload["tracking"]["utm_campaign"]
    if service_slug is None:
        raise Exception("Missing service information on calendly iframe info: tracking->utm_campaign")

    service = MentorshipService.objects.filter(slug=service_slug, academy=academy).first()
    if service is None:
        raise Exception(f"Service with slug {service_slug} not found for academy {academy.name}")

    mentee = None
    mentee_id = "undefined"
    if "salesforce_uuid" in payload["tracking"] and payload["tracking"]["salesforce_uuid"] != "":
        mentee_id = payload["tracking"]["salesforce_uuid"]
        mentee = User.objects.filter(id=mentee_id).first()

    if mentee is None:
        mentee_email = payload["email"]
        mentee = User.objects.filter(email=mentee_email).first()

    if mentee is None:
        raise Exception(f"Mentee user not found with email {mentee_email} or id {mentee_id}")

    event_uuid = urlparse(payload["event"]).path.split("/")[-1]
    event = client.get_event(event_uuid)
    if event is None or "resource" not in event:
        raise Exception(f"Event with uuid {event_uuid} not found on calendly")
    event = event["resource"]

    if not isinstance(event["event_memberships"], list) or len(event["event_memberships"]) == 0:
        raise Exception("No mentor information was found on calendly event")

    mentor_email = event["event_memberships"][0]["user_email"]
    mentor_uuid = urlparse(event["event_memberships"][0]["user"]).path.split("/")[-1]

    mentor = (
        MentorProfile.objects.filter(academy=academy)
        .filter(Q(calendly_uuid=mentor_uuid) | Q(email=mentor_email) | Q(user__email=mentor_email))
        .first()
    )
    if mentor is None:
        raise Exception(f"Mentor not found with uuid {mentor_uuid} and email {mentor_email}")

    if mentor.status in ["INVITED", "INNACTIVE"]:
        raise Exception(f"Mentor status is {mentor.status}")

    if mentor.services.filter(slug=service.slug).first() is None:
        raise Exception(f"Mentor {mentor.name} is not assigned for service {service.slug}")

    meeting_url = None
    if "location" in payload and "join_url" in payload["location"]:
        meeting_url = payload["location"]["join_url"]

    session = MentorshipSession.objects.filter(calendly_uuid=event_uuid).first()
    if session is None:
        session = MentorshipSession()

    session.is_online = True
    session.mentor = mentor
    session.mentee = mentee
    session.online_meeting_url = meeting_url
    session.status_message = "Scheduled throught calendly"
    session.starts_at = event["start_time"]
    session.ends_at = event["end_time"]
    session.service = service
    session.calendly_uuid = event_uuid
    session.save()

    return session
