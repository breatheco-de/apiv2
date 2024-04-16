import logging

from breathecode.admissions.actions import is_no_saas_student_up_to_date_in_any_cohort
from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.models import User
from breathecode.mentorship.models import MentorProfile, MentorshipService
from breathecode.payments.models import Consumable, ConsumptionSession
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.payment_exception import PaymentException
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


def mentorship_service_by_url_param(context: PermissionContextType, args: tuple,
                                    kwargs: dict) -> tuple[dict, tuple, dict]:

    context['will_consume'] = False
    request = context['request']
    consumable = None

    lang = get_user_language(request)

    slug = kwargs.get('mentor_slug')
    mentor_profile = MentorProfile.objects.filter(slug=slug).first()
    if mentor_profile is None:
        raise ValidationException(translation(lang,
                                              en=f'No mentor found with slug {slug}',
                                              es=f'No se encontró mentor con slug {slug}'),
                                  code=404)

    slug = kwargs.get('service_slug')
    mentorship_service = MentorshipService.objects.filter(slug=slug).first()
    if mentorship_service is None:
        raise ValidationException(translation(lang,
                                              en=f'No service found with slug {slug}',
                                              es=f'No se encontró el servicio con slug {slug}'),
                                  code=404)

    kwargs['mentor_profile'] = mentor_profile
    kwargs['mentorship_service'] = mentorship_service

    del kwargs['mentor_slug']
    del kwargs['service_slug']

    # avoid do more stuff if it's a consumption session
    if context['is_consumption_session']:
        return (context, args, kwargs)

    context['request']

    is_saas = mentorship_service and mentorship_service.academy.available_as_saas

    # avoid call LaunchDarkly if mentorship_service is empty
    if mentor_profile.user.id != request.user.id and is_saas:
        context['will_consume'] = True

    if context['will_consume'] is False and is_no_saas_student_up_to_date_in_any_cohort(
            context['request'].user, academy=mentor_profile.academy) is False:
        raise PaymentException(
            translation(lang,
                        en=f'You can\'t access this asset because you finantial status is not up to date',
                        es=f'No puedes acceder a este recurso porque tu estado financiero no está al dia',
                        slug='cohort-user-status-later'))

    context['consumables'] = context['consumables'].filter(
        mentorship_service_set__mentorship_services=mentorship_service)

    if context['will_consume']:
        context['time_of_life'] = mentorship_service.max_duration

    if (mentor_profile.user.id == request.user.id and is_saas and (mentee := request.GET.get('mentee'))
            and not mentee.isdigit()):
        raise ValidationException(translation(lang, en='mentee must be a number', es='mentee debe ser un número'),
                                  code=400)

    if (mentor_profile.user.id == request.user.id and is_saas and mentee
            and not (mentee := User.objects.filter(id=mentee).first())):
        raise ValidationException(translation(lang,
                                              en=f'Mentee not found with id {mentee}',
                                              es=f'No se encontró el mentee con id {mentee}'),
                                  code=400)

    if (mentor_profile.user.id == request.user.id and is_saas and mentee and not (consumable := Consumable.get(
            lang=lang,
            user=mentee,
            permission=context['permission'],
            extra={'mentorship_service_set__mentorship_services': mentorship_service},
    ))):

        raise ValidationException(translation(
            lang,
            en=f'Mentee do not have enough credits to access this service: {context["permission"]}',
            es='El mentee no tiene suficientes créditos para acceder a este servicio: '
            f'{context["permission"]}'),
                                  slug='mentee-not-enough-consumables',
                                  code=402)

    if consumable:
        session = ConsumptionSession.build_session(request, consumable, mentorship_service.max_duration, mentee)
        session.will_consume(1)

    return (context, args, kwargs)
