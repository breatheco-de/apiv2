from django.db.models import Q
from breathecode.utils.decorators import PermissionContextType


def cohort_by_url_param(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
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
