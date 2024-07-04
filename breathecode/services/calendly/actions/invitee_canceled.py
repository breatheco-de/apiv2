import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def invitee_canceled(self, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.mentorship.models import MentorshipSession

    cancellation_email = payload["email"]

    event_uuid = urlparse(payload["event"]).path.split("/")[-1]
    session = MentorshipSession.objects.filter(calendly_uuid=event_uuid).first()
    if session is None:
        raise Exception(f"Mentoring session with calendly_uuid {event_uuid} not found while trying to cancel it")
    session.Summary = f"Session was canceled by {cancellation_email} and it was notified by calendly"
    session.status = "CANCELED"
    session.save()
