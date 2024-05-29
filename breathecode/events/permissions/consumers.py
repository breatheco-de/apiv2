import logging

from django.db.models import Q
from django.utils import timezone

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.actions import get_user_language
from breathecode.events.actions import get_my_event_types
from breathecode.events.models import Event, LiveClass
from breathecode.utils.decorators import ServiceContext
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import PaymentException, ValidationException

logger = logging.getLogger(__name__)


def event_by_url_param(context: ServiceContext, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:
    context['will_consume'] = False

    request = context['request']
    lang = get_user_language(request)
    items = get_my_event_types(request.user)

    pk = Q(id=kwargs.get('event_id')) | Q(slug=kwargs.get('event_slug'), slug__isnull=False)
    belongs_to_this_event = Q(event_type__in=items) | Q(host_user=request.user)
    event = Event.objects.filter(pk, belongs_to_this_event).first()

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

    kwargs['event'] = event

    if 'event_id' in kwargs:
        del kwargs['event_id']

    if 'event_slug' in kwargs:
        del kwargs['event_slug']

    if context['is_consumption_session']:
        return (context, args, kwargs)

    event_type = event.event_type

    is_host = event.host_user == request.user
    is_free_for_all = event.free_for_all
    is_free_for_bootcamps = is_free_for_all or ((event.free_for_bootcamps) or
                                                (event.free_for_bootcamps is None and event_type.free_for_bootcamps))

    user_with_available_as_saas_false = CohortUser.objects.filter(
        Q(cohort__available_as_saas=False)
        | Q(cohort__available_as_saas=None, cohort__academy__available_as_saas=False),
        user=request.user).exists()

    if not is_host and not is_free_for_all and (not is_free_for_bootcamps or not user_with_available_as_saas_false):
        context['will_consume'] = True

    if context['will_consume'] is False and is_no_saas_student_up_to_date_in_any_cohort(context['request'].user,
                                                                                        academy=event.academy) is False:
        raise PaymentException(
            translation(lang,
                        en='You can\'t access this asset because your finantial status is not up to date',
                        es='No puedes acceder a este recurso porque tu estado financiero no está al dia',
                        slug='cohort-user-status-later'))

    context['consumables'] = context['consumables'].filter(event_type_set__event_types=event_type)

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


def live_class_by_url_param(context: ServiceContext, args: tuple, kwargs: dict) -> tuple[dict, tuple, dict]:

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

    kwargs['live_class'] = live_class
    kwargs['lang'] = lang
    del kwargs['hash']

    if context['is_consumption_session']:
        return (context, args, kwargs)

    # avoid to be taken if the cohort is available as saas is not set
    cohort_available_as_saas = (live_class.cohort_time_slot.cohort.available_as_saas is not None
                                and live_class.cohort_time_slot.cohort.available_as_saas)

    # avoid to be taken if the cohort is available as saas is set
    academy_available_as_saas = (live_class.cohort_time_slot.cohort.available_as_saas is None
                                 and live_class.cohort_time_slot.cohort.academy
                                 and live_class.cohort_time_slot.cohort.academy.available_as_saas)

    if cohort_available_as_saas or academy_available_as_saas:
        context['will_consume'] = True

    # CohortSet requires that Academy be available as saas, this line should be uncovered
    if context['will_consume'] is False and is_no_saas_student_up_to_date_in_any_cohort(
            context['request'].user, cohort=live_class.cohort_time_slot.cohort) is False:
        raise PaymentException(
            translation(lang,
                        en='You can\'t access this asset because your finantial status is not up to date',
                        es='No puedes acceder a este recurso porque tu estado financiero no está al dia',
                        slug='cohort-user-status-later'))

    context['consumables'] = context['consumables'].filter(
        cohort_set__cohortsetcohort__cohort=live_class.cohort_time_slot.cohort)

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
