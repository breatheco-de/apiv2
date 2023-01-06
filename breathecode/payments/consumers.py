from datetime import timedelta
from django.db.models import FloatField, Max, Q, Value
from breathecode.payments.models import ConsumptionSession

from breathecode.utils.decorators import PermissionContextType
from django.utils import timezone


def cohort_by_url_param(context: PermissionContextType, args: tuple,
                        kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    context['request'].headers['Content-Type']

    return (context, args, kwargs)


def cohort_by_header(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    context['request'].headers['Content-Type']

    return (context, args, kwargs)


def mentorship_service_by_url_param(context: PermissionContextType, args: tuple,
                                    kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(mentorship_services__id=kwargs.get('service_id'))
        | Q(mentorship_services__slug=kwargs.get('service_slug')))

    consumable = context['consumables'].first()
    consume = None

    if consumable:
        consume = ConsumptionSession.build_session(
            context['request'],
            consumable,
            #    'mentorship.MentorshipService',
            timedelta(days=1),
            #    id=kwargs.get('service_id'),
            #    slug=kwargs.get('service_slug'),
            info='Join to a mentorship')

    return (context, args, kwargs, consume)
