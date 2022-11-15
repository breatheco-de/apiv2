from django.db.models import FloatField, Max, Q, Value

from breathecode.utils.decorators import PermissionContextType


def cohort_consumer(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    return (context, args, kwargs)


def mentorship_service_consumer(context: PermissionContextType, args: tuple,
                                kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(mentorship_services__id=kwargs.get('service_id'))
        | Q(mentorship_services__slug=kwargs.get('service_slug')))

    return (context, args, kwargs)
