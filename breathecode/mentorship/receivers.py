import logging
from django.dispatch import receiver
from django.db.models import Avg
from django.contrib.auth.models import Group
from breathecode.mentorship.models import MentorProfile
from .signals import mentor_profile_saved
# from .models import Answer
# from .tasks import process_student_graduation, process_answer_received, send_mentorship_session_survey

logger = logging.getLogger(__name__)

# @receiver(mentorship_session_status, sender=MentorshipSession)
# def post_mentoring_session_ended(sender, instance, **kwargs):
#     if instance.status == 'COMPLETED':
#         logger.debug('Procesing mentoring session completition')
#         send_mentorship_session_survey.delay(instance.id)


@receiver(mentor_profile_saved, sender=MentorProfile)
def post_save_profile_academy(sender, instance: MentorProfile, created: bool, **kwargs):
    if created:
        group = Group.objects.filter(name='Mentor').first()
        instance.user.groups.add(group)
