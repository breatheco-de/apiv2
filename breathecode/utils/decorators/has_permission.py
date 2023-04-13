from datetime import datetime, timedelta
import logging
import traceback
from typing import Callable, Optional, TypedDict

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework.views import APIView
from django.db.models import Sum
from django.shortcuts import render
from django.http import JsonResponse

from breathecode.authenticate.models import Permission, User
from breathecode.payments.signals import consume_service

from ..exceptions import ProgramingError
from ..payment_exception import PaymentException
from ..validation_exception import ValidationException
from rest_framework.response import Response

__all__ = ['has_permission', 'validate_permission', 'HasPermissionCallback', 'PermissionContextType']

logger = logging.getLogger(__name__)


def show(name, data):
    print(name, data)
    logger.info(str(name))
    logger.info(str(data))


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


def render_message(r, msg, btn_label=None, btn_url=None, btn_target='_blank', data={}, status=None):
    _data = {'MESSAGE': msg, 'BUTTON': btn_label, 'BUTTON_TARGET': btn_target, 'LINK': btn_url}

    return render(r, 'message.html', {**_data, **data}, status=status)


#TODO: change html param for string with selected encode
def has_permission(permission: str,
                   consumer: bool | HasPermissionCallback = False,
                   format='json') -> callable:
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

            try:
                utc_now = timezone.now()
                session = ConsumptionSession.get_session(request)
                if session:
                    return function(*args, **kwargs)

                if validate_permission(request.user, permission, consumer):
                    show('inner', 'inner')
                    context = {
                        'utc_now': utc_now,
                        'consumer': consumer,
                        'permission': permission,
                        'request': request,
                        'consumables': Consumable.objects.none(),
                        'time_of_life': None,
                        'will_consume': True,
                    }

                    show('consumer', consumer)
                    if consumer:
                        items = Consumable.objects.filter(
                            Q(valid_until__lte=utc_now) | Q(valid_until=None),
                            user=request.user,
                            service_item__service__groups__permissions__codename=permission).exclude(
                                how_many=0).order_by('id')

                        context['consumables'] = items

                    show("context['consumables']", context['consumables'])
                    if callable(consumer):
                        context, args, kwargs = consumer(context, args, kwargs)

                    show("context['time_of_life']", context['time_of_life'])
                    if consumer and context['time_of_life']:
                        consumables = context['consumables']
                        for item in consumables.filter(consumptionsession__status='PENDING', how_many__gt=0):

                            sum = item.consumptionsession_set.filter(status='PENDING').aggregate(
                                Sum('consumptionsession__how_many'))

                            if item.how_many - sum['how_many__sum'] == 0:
                                context['consumables'] = context['consumables'].exclude(id=item.id)

                    show("context['will_consume']", context['will_consume'])
                    if consumer and context['will_consume'] and not context['consumables']:
                        #TODO: send a url to recharge this service
                        show('inside of consumer', 'not-enough-consumables')
                        raise PaymentException(
                            f'You do not have enough credits to access this service: {permission}',
                            slug='with-consumer-not-enough-consumables')

                    show("context['time_of_life']", context['time_of_life'])
                    if consumer and context['will_consume'] and context['time_of_life'] and (
                            consumable := context['consumables'].first()):
                        session = ConsumptionSession.build_session(request, consumable,
                                                                   context['time_of_life'])

                    response = function(*args, **kwargs)

                    show('response.status_code', response.status_code)
                    it_will_consume = context['will_consume'] and consumer and response.status_code < 400
                    show('it_will_consume', it_will_consume)
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
                    show('out of consumer', 'not-enough-consumables')
                    raise PaymentException(
                        f'You do not have enough credits to access this service: {permission}',
                        slug='not-enough-consumables')

            # handle html views errors
            except PaymentException as e:
                if format == 'websocket':
                    raise e

                if format == 'html':
                    return render_message(request, str(e), status=402)

                return Response({'detail': str(e), 'status_code': 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == 'websocket':
                    raise e

                status = e.status_code if hasattr(e, 'status_code') else 400

                if format == 'html':
                    return render_message(request, str(e), status=status)

                return Response({'detail': str(e), 'status_code': status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == 'html':
                    return render_message(request,
                                          'unexpected error, contact admin if you are affected',
                                          status=500)

                response = JsonResponse({'detail': str(e), 'status_code': 500})
                response.status_code = 500
                return response

        return wrapper

    return decorator
