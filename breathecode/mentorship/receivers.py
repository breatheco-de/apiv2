import logging
# from .models import Answer
# from .tasks import process_student_graduation, process_answer_received, send_mentorship_session_survey

logger = logging.getLogger(__name__)

# @receiver(mentorship_session_status, sender=MentorshipSession)
# def post_mentoring_session_ended(sender, instance, **kwargs):
#     if instance.status == 'COMPLETED':
#         logger.debug('Procesing mentoring session completition')
#         send_mentorship_session_survey.delay(instance.id)
