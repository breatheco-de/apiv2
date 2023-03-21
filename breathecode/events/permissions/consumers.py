from datetime import timedelta
from django.db.models import Q
from breathecode.events.models import Event, EventType
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType

from .flags import api


def event_by_url_param(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    event_type = EventType.objects.filter(
        Q(event_type__id=kwargs.get('event_type_id'))
        | Q(event_type__slug=kwargs.get('event_type_slug'))).first()

    event = Event.objects.filter(Q(event__id=kwargs.get('event_id'))
                                 | Q(event__slug=kwargs.get('event_slug')),
                                 event_type=event_type).first()

    # don't act over this, let view choose what to do
    if not event_type or not event:
        context['consumables'] = Consumable.objects.none()
        return (context, args, kwargs)

    context['consumables'] = context['consumables'].filter(event_type_set__event_types=event_type)
    context['will_consume'] = api.release.enable_consume_live_events(context['request'].user)

    return (context, args, kwargs)


def live_class_by_url_param(context: PermissionContextType, args: tuple,
                            kwargs: dict) -> tuple[dict, tuple, dict]:
    context['consumables'] = context['consumables'].filter(
        Q(cohort__id=kwargs.get('cohort_id'))
        | Q(cohort__slug=kwargs.get('cohort_slug')))

    context['will_consume'] = api.release.enable_consume_live_classes(context['request'].user)

    return (context, args, kwargs)
