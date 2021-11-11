import logging
from django.dispatch import receiver
from django.db.models import Avg
from breathecode.mentorship.models import MentorshipSession
from breathecode.mentorship.signals import mentorship_session_status
from .tasks import send_mentorship_starting_notification

logger = logging.getLogger(__name__)


@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentorin_session_status(sender, instance, **kwargs):
    logger.debug('Procesing mentoring session status change')
    if instance.status == 'STARTED':
        send_mentorship_starting_notification.delay(instance.id)
