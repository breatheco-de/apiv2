from datetime import timedelta
import logging
from django.db.models import Q
from breathecode.authenticate.actions import get_user_language
from breathecode.events.actions import get_my_event_types
from breathecode.events.models import Event, EventType, LiveClass
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone

from .flags import api

logger = logging.getLogger(__name__)


def show(name, data):
    print(name, data)
    logger.info(str(name))
    logger.info(str(data))


def event_by_url_param(context: PermissionContextType, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    context['will_consume'] = False

    request = context['request']
    lang = get_user_language(request)
    items = get_my_event_types(request.user)

    event = Event.objects.filter(Q(id=kwargs.get('event_id'))
                                 | Q(slug=kwargs.get('event_slug'), slug__isnull=False),
                                 event_type__in=items).first()

    if not event:
        raise ValidationException(translation(lang,
                                              en='Event not found or you dont have access',
                                              es='Evento no encontrado o no tienes acceso',
                                              slug='not-found'),
                                  code=404)

    if not event.live_stream_url:
        raise ValidationException(
            translation(lang,
                        en='Event live stream URL was not found',
                        es='No se encontró la URL de transmisión en vivo del evento',
                        slug='event-online-meeting-url-not-found'))

    event_type = event.event_type

    import os
    show("os.getenv('LAUNCH_DARKLY_API_KEY')", os.getenv('LAUNCH_DARKLY_API_KEY'))
    show('event', event)
    show('event_type', event_type)
    show('before', context['consumables'])
    context['consumables'] = context['consumables'].filter(event_type_set__event_types=event_type)
    show('after', context['consumables'])

    if event.academy and event.academy.available_as_saas:
        # context['will_consume'] = api.release.enable_consume_live_events(context['request'].user, event)
        context['will_consume'] = True

    show('will_consume', context['will_consume'])

    kwargs['event'] = event

    if 'event_id' in kwargs:
        del kwargs['event_id']

    if 'event_slug' in kwargs:
        del kwargs['event_slug']

    utc_now = timezone.now()
    if event.ending_at < utc_now:
        raise ValidationException(translation(lang,
                                              en='This event has already finished',
                                              es='Este evento ya ha terminado',
                                              slug='event-has-ended'),
                                  code=400)

    if context['will_consume']:
        delta = event.ending_at - utc_now
        context['time_of_life'] = delta

    return (context, args, kwargs)


def live_class_by_url_param(context: PermissionContextType, args: tuple,
                            kwargs: dict) -> tuple[dict, tuple, dict]:

    context['will_consume'] = False

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

    if not live_class.cohort_time_slot.cohort.online_meeting_url:
        raise ValidationException(
            translation(lang,
                        en='Cohort online meeting URL was not found',
                        es='No se encontró la URL de la reunión en línea del cohorte',
                        slug='cohort-online-meeting-url-not-found'))

    context['consumables'] = context['consumables'].filter(cohort=live_class.cohort_time_slot.cohort)

    kwargs['live_class'] = live_class
    kwargs['lang'] = lang
    del kwargs['hash']

    # avoid to be taken if the cohort is available as saas is not set
    cohort_available_as_saas = (live_class.cohort_time_slot.cohort.available_as_saas is not None
                                and live_class.cohort_time_slot.cohort.available_as_saas)

    # avoid to be taken if the cohort is available as saas is set
    academy_available_as_saas = (live_class.cohort_time_slot.cohort.available_as_saas is None
                                 and live_class.cohort_time_slot.cohort.academy
                                 and live_class.cohort_time_slot.cohort.academy.available_as_saas)

    if cohort_available_as_saas or academy_available_as_saas:
        # context['will_consume'] = api.release.enable_consume_live_classes(context['request'].user)
        context['will_consume'] = True

    utc_now = timezone.now()
    if live_class.ending_at < utc_now:
        raise ValidationException(translation(lang,
                                              en='Class has ended',
                                              es='La clase ha terminado',
                                              slug='class-has-ended'),
                                  code=400)

    if context['will_consume']:
        delta = live_class.ending_at - utc_now
        context['time_of_life'] = delta

    return (context, args, kwargs)
