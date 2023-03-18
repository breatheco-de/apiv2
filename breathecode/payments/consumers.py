from datetime import timedelta
from django.db.models import FloatField, Max, Q, Value
from breathecode.authenticate.models import User
from breathecode.events.models import LiveClass
from breathecode.authenticate.actions import get_user_language
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.flags import api
from breathecode.payments.models import ConsumptionSession

from breathecode.utils.decorators import PermissionContextType
from django.utils import timezone

from breathecode.utils.validation_exception import ValidationException
from breathecode.services import LaunchDarkly


def live_class_by_url_param(context: PermissionContextType, args: tuple,
                            kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    context['will_consume'] = api.release.enable_consume_live_classes(context['request'].user)

    return (context, args, kwargs)


def cohort_by_url_param(context: PermissionContextType, args: tuple,
                        kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    return (context, args, kwargs)


def cohort_by_header(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    cohort = context['request'].META.get('HTTP_COHORT', '')
    kwargs = {}

    if cohort.isnumeric():
        kwargs['cohort__id'] = int(cohort)

    else:
        kwargs['cohort__slug'] = cohort

    context['consumables'] = context['consumables'].filter(**kwargs)

    return (context, args, kwargs)


def mentorship_service_by_url_param(context: PermissionContextType, args: tuple,
                                    kwargs: dict) -> tuple[dict, tuple, dict]:
    mentorship_service = MentorshipService.objects.filter(
        Q(id=kwargs.get('service_id')) | Q(slug=kwargs.get('service_slug'))).first()
    context['consumables'] = context['consumables'].filter(mentorship_services=mentorship_service)

    context['time_of_life'] = timedelta(hours=2)

    # avoid call LaunchDarkly if mentorship_service is empty
    if mentorship_service:
        context['will_consume'] = api.release.enable_consume_mentorships(context['request'].user,
                                                                         mentorship_service)

    else:
        context['will_consume'] = False

    return (context, args, kwargs)


def cohort_schedule_by_url_param(context: PermissionContextType, args: tuple,
                                 kwargs: dict) -> tuple[dict, tuple, dict]:

    # lang = get_user_language(request)

    # schedule = LiveClass.objects.filter(id=cohort_schedule_id).first()
    # if not schedule:
    #     raise ValidationException(lang,
    #                                 en='Schedule not found',
    #                                 es='Horario no encontrado',
    #                                 slug='schedule_not_found')

    context['consumables'] = context['consumables'].filter(id=kwargs.get('service_id'))

    context['time_of_life'] = timedelta(hours=2)

    return (context, args, kwargs)
