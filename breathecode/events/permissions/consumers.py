from datetime import timedelta
from django.db.models import Q
from breathecode.authenticate.actions import get_user_language
from breathecode.events.models import Event, EventType, LiveClass
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

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

    request = context['request']
    lang = get_user_language(request)

    live_class = LiveClass.objects.filter(cohort_time_slot__cohort__cohortuser__user=request.user,
                                          hash=kwargs.get('hash')).first()
    if not live_class:
        raise ValidationException(translation(lang,
                                              en='Live class not found',
                                              es='Clase en vivo no encontrada',
                                              slug='not-found'),
                                  code=404)

    context['consumables'] = context['consumables'].filter(cohort=live_class.cohort_time_slot.cohort)

    kwargs['live_class'] = live_class
    del kwargs['hash']

    context['will_consume'] = api.release.enable_consume_live_classes(context['request'].user)

    return (context, args, kwargs)
