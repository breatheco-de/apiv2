import logging
import time
from django.db.models import Q
from urllib.parse import urlparse
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def invitee_canceled(self, webhook, payload: dict):
    # lazyload to fix circular import
    from breathecode.mentorship.models import MentorshipSession
    # from breathecode.events.actions import update_or_create_event
    # payload = payload['resource']

    academy = webhook.organization.academy

    mentee_email = payload['email']

    event_uuid = urlparse(payload['event']).path.split('/')[-1]
    session = MentorshipSession.objects.filter(calendly_uuid=event_uuid).first()
    if session is None:
        raise Exception(f'Mentoring session with calendly_uuid {event_uuid} not found')
    session.Summary = f'Session was canceled by {mentee_email} and it was notified by calendly'
    session.status = 'CANCELED'
    session.save()
