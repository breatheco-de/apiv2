from datetime import timedelta
from django.db.models import Q
from breathecode.authenticate.actions import get_user_language
from breathecode.events.models import Event, EventType
from breathecode.mentorship.models import MentorProfile, MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

from .flags import api


def mentorship_service_by_url_param(context: PermissionContextType, args: tuple,
                                    kwargs: dict) -> tuple[dict, tuple, dict]:

    context['will_consume'] = False
    request = context['request']

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

    context['consumables'] = context['consumables'].filter(
        mentorship_service_set__mentorship_services=mentorship_service)

    # avoid call LaunchDarkly if mentorship_service is empty
    if (mentor_profile.user.id != request.user.id and mentorship_service
            and mentorship_service.academy.available_as_saas):
        context['will_consume'] = api.release.enable_consume_mentorships(context['request'].user,
                                                                         mentorship_service)
        # context['will_consume'] = True

    else:
        context['will_consume'] = False

    if context['will_consume']:
        context['time_of_life'] = mentorship_service.max_duration

    kwargs['mentor_profile'] = mentor_profile
    kwargs['mentorship_service'] = mentorship_service

    del kwargs['mentor_slug']
    del kwargs['service_slug']

    return (context, args, kwargs)
