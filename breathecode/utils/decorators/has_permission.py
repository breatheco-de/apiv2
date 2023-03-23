from datetime import datetime, timedelta
from typing import Callable, Optional, TypedDict

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework.views import APIView
from django.db.models import Sum

from breathecode.authenticate.models import Permission, User
from breathecode.payments.signals import consume_service

from ..exceptions import ProgramingError
from ..payment_exception import PaymentException
from ..validation_exception import ValidationException

__all__ = ['has_permission', 'validate_permission', 'HasPermissionCallback', 'PermissionContextType']


class PermissionContextType(TypedDict):
    utc_now: datetime
    consumer: bool
    permission: str
    request: WSGIRequest
    consumables: QuerySet
    time_of_life: Optional[timedelta]
    will_consume: bool


HasPermissionCallback = Callable[[PermissionContextType, tuple, dict], tuple[PermissionContextType, tuple,
                                                                             dict, Optional[timedelta]]]


def validate_permission(user: User, permission: str, consumer: bool | HasPermissionCallback = False) -> bool:
    if consumer:
        return User.objects.filter(id=user.id, groups__permissions__codename=permission).exists()

    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).exists() or found.group_set.filter(user__id=user.id).exists()


def has_permission(permission: str, consumer: bool | HasPermissionCallback = False) -> callable:
    """This decorator check if the current user can access to the resource through of permissions"""

    from breathecode.payments.models import Consumable, ConsumptionSession

    def decorator(function: callable) -> callable:

        def wrapper(*args, **kwargs):
            if isinstance(permission, str) == False:
                raise ProgramingError('Permission must be a string')

            try:
                if hasattr(args[0], '__class__') and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], 'user') and hasattr(args[0].user, 'has_perm'):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgramingError('Missing request information, use this decorator with DRF View')

            utc_now = timezone.now()
            session = ConsumptionSession.get_session(request)
            if session:
                return function(*args, **kwargs)

            if validate_permission(request.user, permission, consumer):
                context = {
                    'utc_now': utc_now,
                    'consumer': consumer,
                    'permission': permission,
                    'request': request,
                    'consumables': Consumable.objects.none(),
                    'time_of_life': None,
                    'will_consume': True,
                }

                if consumer:
                    items = Consumable.objects.filter(
                        Q(valid_until__lte=utc_now) | Q(valid_until=None),
                        user=request.user,
                        service_item__service__groups__permissions__codename=permission).exclude(
                            how_many=0).order_by('id')

                    context['consumables'] = items

                if callable(consumer):
                    context, args, kwargs = consumer(context, args, kwargs)

                if consumer and context['time_of_life']:
                    consumables = context['consumables']
                    for item in consumables.filter(consumptionsession__status='PENDING', how_many__gt=0):

                        sum = item.consumptionsession_set.filter(status='PENDING').aggregate(
                            Sum('consumptionsession__how_many'))

                        if item.how_many - sum['how_many__sum'] == 0:
                            context['consumables'] = context['consumables'].exclude(id=item.id)

                if consumer and context['will_consume'] and not context['consumables']:
                    #TODO: send a url to recharge this service
                    raise PaymentException(
                        f'You do not have enough credits to access this service: {permission}',
                        slug='with-consumer-not-enough-consumables')

                if consumer and context['will_consume'] and context['time_of_life'] and (
                        consumable := context['consumables'].first()):
                    session = ConsumptionSession.build_session(request, consumable, context['time_of_life'])

                response = function(*args, **kwargs)

                it_will_consume = context['will_consume'] and consumer and response.status_code < 400
                if it_will_consume and session:
                    session.will_consume(1)

                elif it_will_consume:
                    item = context['consumables'].first()
                    consume_service.send(instance=item, sender=item.__class__, how_many=1)

                return response

            elif not consumer and isinstance(request.user, AnonymousUser):
                raise ValidationException(f'Anonymous user don\'t have this permission: {permission}',
                                          code=403,
                                          slug='anonymous-user-without-permission')

            elif not consumer:
                raise ValidationException((f'You (user: {request.user.id}) don\'t have this permission: '
                                           f'{permission}'),
                                          code=403,
                                          slug='without-permission')

            elif consumer and isinstance(request.user, AnonymousUser):
                raise PaymentException(
                    f'Anonymous user do not have enough credits to access this service: {permission}',
                    slug='anonymous-user-not-enough-consumables')

            else:
                raise PaymentException(f'You do not have enough credits to access this service: {permission}',
                                       slug='not-enough-consumables')

        return wrapper

    return decorator
