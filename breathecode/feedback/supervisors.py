from datetime import timedelta

from django.utils import timezone

from breathecode.feedback.models import Answer, MentorshipSession
from breathecode.utils.decorators import issue, supervisor

from .tasks import send_mentorship_session_survey

MIN_PENDING_SESSIONS = 30
MIN_CANCELLED_SESSIONS = 10


@supervisor(delta=timedelta(days=1))
def supervise_mentorship_survey():
    utc_now = timezone.now()
    sessions = MentorshipSession.objects.filter(
        status="COMPLETED",
        started_at__isnull=False,
        ended_at__isnull=False,
        mentor__isnull=False,
        mentee__isnull=False,
        created_at__lte=utc_now,
        created_at__gte=utc_now - timedelta(days=5),
    )

    for session in sessions:
        duration = session.ended_at - session.started_at

        if (
            duration > timedelta(minutes=5)
            and Answer.objects.filter(mentorship_session__id=session.id).exists() is False
        ):
            yield f"Session {session.id} hasn't a survey", "no-survey-for-session", {"session_id": session.id}


@issue(supervise_mentorship_survey, delta=timedelta(minutes=10))
def no_survey_for_session(session_id: int):
    session = MentorshipSession.objects.filter(id=session_id).first()
    if session is None:
        return

    if Answer.objects.filter(mentorship_session__id=session.id).exists():
        return True

    send_mentorship_session_survey.delay(session.id)
