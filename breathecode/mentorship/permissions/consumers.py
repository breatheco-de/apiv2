from datetime import timedelta
from django.db.models import Q
from breathecode.events.models import Event, EventType
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType

from .flags import api


def mentorship_service_by_url_param(context: PermissionContextType, args: tuple,
                                    kwargs: dict) -> tuple[dict, tuple, dict]:
    mentorship_service = MentorshipService.objects.filter(
        Q(id=kwargs.get('service_id')) | Q(slug=kwargs.get('service_slug')),
        Q(id=kwargs.get('mentor_id')) | Q(slug=kwargs.get('mentor_slug'))).first()
    context['consumables'] = context['consumables'].filter(mentorship_services=mentorship_service)

    # avoid call LaunchDarkly if mentorship_service is empty
    if mentorship_service:
        context['will_consume'] = api.release.enable_consume_mentorships(context['request'].user,
                                                                         mentorship_service)

    else:
        context['will_consume'] = False

    if context['will_consume']:
        context['time_of_life'] = mentorship_service.max_duration

    return (context, args, kwargs)
