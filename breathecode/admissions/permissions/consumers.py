from datetime import timedelta
from django.db.models import Q
from breathecode.events.models import Event, EventType
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType

from .flags import api


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


#FIXME: ???
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
