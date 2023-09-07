from typing import Any, Optional

from breathecode.utils.decorators.task import AbortTask

ALLOWED_TYPES = {
    'auth.UserInvite': [
        'invite_created',
        'invite_status_updated',
    ],
    'feedback.Answer': [
        'nps_answered',
    ],
    'auth.User': [
        'login',
    ],
    'admissions.Cohort': [
        'open_syllabus_module',
    ],
    'assignments.Task': [
        'read_assignment',
        'assignment_review_status_updated',
        'assignment_status_updated',
    ],
    'events.EventCheckin': [
        'event_checkin_created',
        'event_checkin_assisted',
    ],
    'payments.Bag': [
        'bag_created',
    ],
    'payments.Subscription': [
        'checkout_completed',
    ],
    'payments.PlanFinancing': [
        'checkout_completed',
    ],
    'mentorship.MentorshipSession': [
        'mentoring_session_scheduled',
        'mentorship_session_checkin',
        'mentorship_session_checkout',
    ],
}


class FillActivityMeta:

    @staticmethod
    def _get_query(related_id: Optional[str | int] = None,
                   related_slug: Optional[str] = None) -> dict[str, Any]:
        kwargs = {}

        if related_id:
            kwargs['pk'] = related_id

        if related_slug:
            kwargs['slug'] = related_slug

        return kwargs

    @classmethod
    def user_invite(cls,
                    kind: str,
                    related_id: Optional[str | int] = None,
                    related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.authenticate.models import UserInvite

        kwargs = cls._get_query(related_id, related_slug)
        instance = UserInvite.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'UserInvite {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'email': instance.email,
            'phone': instance.phone,
            'status': instance.status,
            'process_status': instance.process_status,
            'author_email': instance.author.email if instance.author else None,
            'author_username': instance.author.username if instance.author else None,
            'user_email': instance.user.email if instance.user else None,
            'user_username': instance.user.username if instance.user else None,
            'user_first_name': instance.user.first_name if instance.user else None,
            'user_last_name': instance.user.last_name if instance.user else None,
            'role': instance.role.slug if instance.role else None,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
            'academy': instance.cohort.slug if instance.academy else None,
            'cohort': instance.cohort.slug if instance.cohort else None,
        }

    @classmethod
    def answer(cls,
               kind: str,
               related_id: Optional[str | int] = None,
               related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.feedback.models import Answer

        kwargs = cls._get_query(related_id, related_slug)
        instance = Answer.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'Answer {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'title': instance.title,
            'lowest': instance.lowest,
            'highest': instance.highest,
            'lang': instance.lang,
            'event': instance.event.slug if instance.event else None,
            'mentorship_session': instance.mentorship_session.name if instance.mentorship_session else None,
            'mentor_email': instance.mentor.email if instance.user else None,
            'mentor_username': instance.mentor.username if instance.user else None,
            'mentor_first_name': instance.mentor.first_name if instance.user else None,
            'mentor_last_name': instance.mentor.last_name if instance.user else None,
            'cohort': instance.cohort.slug if instance.cohort else None,
            'academy': instance.academy.slug if instance.academy else None,
            'score': instance.score,
            'comment': instance.comment,
            'survey': instance.survey.id if instance.survey else None,
            'status': instance.status,
            'user_email': instance.user.email if instance.user else None,
            'user_username': instance.user.username if instance.user else None,
            'user_first_name': instance.user.first_name if instance.user else None,
            'user_last_name': instance.user.last_name if instance.user else None,
            'opened_at': instance.opened_at.isoformat() if instance.opened_at else None,
            'sent_at': instance.sent_at.isoformat() if instance.sent_at else None,
        }

    @classmethod
    def user(cls,
             kind: str,
             related_id: Optional[str | int] = None,
             related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.authenticate.models import User

        kwargs = cls._get_query(related_id, related_slug)
        instance = User.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'User {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'email': instance.email,
            'username': instance.username,
        }

    @classmethod
    def cohort(cls,
               kind: str,
               related_id: Optional[str | int] = None,
               related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.admissions.models import Cohort

        kwargs = cls._get_query(related_id, related_slug)
        instance = Cohort.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'Cohort {related_id or related_slug} not found')

        syllabus = (f'{instance.syllabus_version.syllabus.slug}.v{instance.syllabus_version.version}'
                    if instance.syllabus_version else None)
        return {
            'id': instance.id,
            'slug': instance.slug,
            'name': instance.name,
            'kickoff_date': instance.kickoff_date.isoformat(),
            'ending_date': instance.ending_date.isoformat() if instance.ending_date else None,
            'current_day': instance.current_day,
            'current_module': instance.current_module,
            'stage': instance.stage,
            'private': instance.private,
            'accepts_enrollment_suggestions': instance.accepts_enrollment_suggestions,
            'never_ends': instance.never_ends,
            'remote_available': instance.remote_available,
            'online_meeting_url': instance.online_meeting_url,
            'timezone': instance.timezone,
            'academy': instance.academy.slug if instance.academy else None,
            'syllabus': syllabus,
            'intro_video': instance.intro_video,
            'schedule': instance.schedule.name if instance.schedule else None,
            'is_hidden_on_prework': instance.is_hidden_on_prework,
            'available_as_saas': instance.available_as_saas,
            'language': instance.language,
        }

    @classmethod
    def task(cls,
             kind: str,
             related_id: Optional[str | int] = None,
             related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.assignments.models import Task

        kwargs = cls._get_query(related_id, related_slug)
        instance = Task.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'Task {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'user_email': instance.user.email if instance.user else None,
            'user_username': instance.user.username if instance.user else None,
            'user_first_name': instance.user.first_name if instance.user else None,
            'user_last_name': instance.user.last_name if instance.user else None,
            'associated_slug': instance.associated_slug,
            'title': instance.title,
            'task_status': instance.task_status,
            'revision_status': instance.revision_status,
            'task_type': instance.task_type,
            'github_url': instance.github_url,
            'live_url': instance.live_url,
            'opened_at': instance.opened_at.isoformat() if instance.opened_at else None,
            'cohort': instance.cohort.slug if instance.cohort else None,
        }

    @classmethod
    def event_checkin(cls,
                      kind: str,
                      related_id: Optional[str | int] = None,
                      related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.events.models import EventCheckin

        kwargs = cls._get_query(related_id, related_slug)
        instance = EventCheckin.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'EventCheckin {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'email': instance.email,
            'attendee_email': instance.attendee.email if instance.attendee else None,
            'attendee_username': instance.attendee.username if instance.attendee else None,
            'attendee_first_name': instance.attendee.first_name if instance.attendee else None,
            'attendee_last_name': instance.attendee.last_name if instance.attendee else None,
            'event_id': instance.event.id,
            'event_slug': instance.event.slug,
            'status': instance.status,
            'attended_at': instance.attended_at.isoformat() if instance.attended_at else None,
        }

    @classmethod
    def mentorship_session(cls,
                           kind: str,
                           related_id: Optional[str | int] = None,
                           related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.mentorship.models import MentorshipSession

        kwargs = cls._get_query(related_id, related_slug)
        instance = MentorshipSession.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'MentorshipSession {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'name': instance.name,
            'is_online': instance.is_online,
            'latitude': instance.latitude,
            'longitude': instance.longitude,
            'mentor_id': instance.mentor.id if instance.mentor else None,
            'mentor_slug': instance.mentor.slug if instance.mentor else None,
            'mentor_name': instance.mentor.name if instance.mentor else None,
            'service': instance.service.slug if instance.service else None,
            'mentee_email': instance.mentee.email if instance.mentee else None,
            'mentee_username': instance.mentee.username if instance.mentee else None,
            'mentee_first_name': instance.mentee.first_name if instance.mentee else None,
            'mentee_last_name': instance.mentee.last_name if instance.mentee else None,
            'online_meeting_url': instance.online_meeting_url,
            'online_recording_url': instance.online_recording_url,
            'status': instance.status,
            'allow_billing': instance.allow_billing,
            'bill': instance.bill.id if instance.bill else None,
            'suggested_accounted_duration': instance.suggested_accounted_duration,
            'accounted_duration': instance.accounted_duration,
            'starts_at': instance.starts_at.isoformat() if instance.starts_at else None,
            'ends_at': instance.ends_at.isoformat() if instance.ends_at else None,
            'started_at': instance.started_at.isoformat() if instance.started_at else None,
            'ended_at': instance.ended_at.isoformat() if instance.ended_at else None,
            'mentor_joined_at': instance.mentor_joined_at.isoformat() if instance.mentor_joined_at else None,
            'mentor_left_at': instance.mentor_left_at.isoformat() if instance.mentor_left_at else None,
            'mentee_left_at': instance.mentee_left_at.isoformat() if instance.mentee_left_at else None,
        }

    @classmethod
    def bag(cls,
            kind: str,
            related_id: Optional[str | int] = None,
            related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.payments.models import Bag

        kwargs = cls._get_query(related_id, related_slug)
        instance = Bag.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'Bag {related_id or related_slug} not found')

        return {
            'id': instance.id,
            'status': instance.status,
            'type': instance.type,
            'chosen_period': instance.chosen_period,
            'how_many_installments': instance.how_many_installments,
            'academy': instance.academy.slug,
            'user_email': instance.user.email,
            'user_username': instance.user.username,
            'user_first_name': instance.user.first_name,
            'user_last_name': instance.user.last_name,
            'is_recurrent': instance.is_recurrent,
            'was_delivered': instance.was_delivered,
            'expires_at': instance.expires_at.isoformat() if instance.expires_at else None,
        }

    @classmethod
    def subscription(cls,
                     kind: str,
                     related_id: Optional[str | int] = None,
                     related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.payments.models import Subscription

        kwargs = cls._get_query(related_id, related_slug)
        instance = Subscription.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'Subscription {related_id or related_slug} not found')

        selected_mentorship_service_set = (instance.selected_mentorship_service_set.slug
                                           if instance.selected_mentorship_service_set else None)

        selected_event_type_set = (instance.selected_event_type_set.slug
                                   if instance.selected_event_type_set else None)
        return {
            'id': instance.id,
            'status': instance.status,
            'user_email': instance.user.email,
            'user_username': instance.user.username,
            'user_first_name': instance.user.first_name,
            'user_last_name': instance.user.last_name,
            'academy': instance.academy.slug,
            'selected_cohort': instance.selected_cohort.slug if instance.selected_cohort else None,
            'selected_mentorship_service_set': selected_mentorship_service_set,
            'selected_event_type_set': selected_event_type_set,
            'paid_at': instance.paid_at.isoformat(),
            'is_refundable': instance.is_refundable,
            'next_payment_at': instance.next_payment_at.isoformat(),
            'valid_until': instance.valid_until.isoformat() if instance.valid_until else None,
            'pay_every': instance.pay_every,
            'pay_every_unit': instance.pay_every_unit,
        }

    @classmethod
    def plan_financing(cls,
                       kind: str,
                       related_id: Optional[str | int] = None,
                       related_slug: Optional[str] = None) -> dict[str, Any]:
        from breathecode.payments.models import PlanFinancing

        kwargs = cls._get_query(related_id, related_slug)
        instance = PlanFinancing.objects.filter(**kwargs).first()

        if not instance:
            raise AbortTask(f'PlanFinancing {related_id or related_slug} not found')

        selected_mentorship_service_set = (instance.selected_mentorship_service_set.slug
                                           if instance.selected_mentorship_service_set else None)

        selected_event_type_set = (instance.selected_event_type_set.slug
                                   if instance.selected_event_type_set else None)
        return {
            'id': instance.id,
            'status': instance.status,
            'user_email': instance.user.email,
            'user_username': instance.user.username,
            'user_first_name': instance.user.first_name,
            'user_last_name': instance.user.last_name,
            'academy': instance.academy.slug,
            'selected_cohort': instance.selected_cohort.slug if instance.selected_cohort else None,
            'selected_mentorship_service_set': selected_mentorship_service_set,
            'selected_event_type_set': selected_event_type_set,
            'next_payment_at': instance.next_payment_at.isoformat(),
            'valid_until': instance.valid_until.isoformat(),
            'plan_expires_at': instance.plan_expires_at.isoformat() if instance.plan_expires_at else None,
            'monthly_price': instance.monthly_price,
        }


def get_activity_meta(kind: str,
                      related_type: Optional[str] = None,
                      related_id: Optional[str | int] = None,
                      related_slug: Optional[str] = None) -> dict[str, Any]:

    if not related_type:
        return {}

    if related_type and not related_id and not related_slug:
        raise AbortTask('related_id or related_slug must be present')

    if related_type not in ALLOWED_TYPES:
        raise AbortTask(f'{related_type} is not supported yet')

    args = (kind, related_id, related_slug)

    if related_type == 'auth.UserInvite' and kind in ALLOWED_TYPES['auth.UserInvite']:
        return FillActivityMeta.user_invite(*args)

    if related_type == 'feedback.Answer' and kind in ALLOWED_TYPES['feedback.Answer']:
        return FillActivityMeta.answer(*args)

    if related_type == 'auth.User' and kind in ALLOWED_TYPES['auth.User']:
        return FillActivityMeta.user(*args)

    if related_type == 'admissions.Cohort' and kind in ALLOWED_TYPES['admissions.Cohort']:
        return FillActivityMeta.cohort(*args)

    if related_type == 'assignments.Task' and kind in ALLOWED_TYPES['assignments.Task']:
        return FillActivityMeta.task(*args)

    if related_type == 'events.EventCheckin' and kind in ALLOWED_TYPES['events.EventCheckin']:
        return FillActivityMeta.event_checkin(*args)

    if related_type == 'payments.Bag' and kind in ALLOWED_TYPES['payments.Bag']:
        return FillActivityMeta.bag(*args)

    if related_type == 'payments.Subscription' and kind in ALLOWED_TYPES['payments.Subscription']:
        return FillActivityMeta.subscription(*args)

    if related_type == 'payments.PlanFinancing' and kind in ALLOWED_TYPES['payments.PlanFinancing']:
        return FillActivityMeta.plan_financing(*args)

    if related_type == 'mentorship.MentorshipSession' and kind in ALLOWED_TYPES[
            'mentorship.MentorshipSession']:
        return FillActivityMeta.mentorship_session(*args)

    raise AbortTask(f'kind {kind} is not supported by {related_type} yet')
