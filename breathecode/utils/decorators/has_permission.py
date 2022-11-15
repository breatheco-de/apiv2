from datetime import datetime
from typing import Callable, TypedDict

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework.views import APIView

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


HasPermissionCallback = Callable[[PermissionContextType, tuple, dict], tuple[PermissionContextType, tuple,
                                                                             dict]]


def validate_permission(user: User, permission: str, consumer: bool | HasPermissionCallback = False) -> bool:
    if consumer:
        return User.objects.filter(id=user.id, groups__permissions__codename=permission).exists()

    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).exists() or found.group_set.filter(user__id=user.id).exists()


#TODO: check if required_payment is needed
def has_permission(permission: str, consumer: bool | HasPermissionCallback = False) -> callable:
    """This decorator check if the current user can access to the resource through of permissions"""

    from breathecode.payments.models import Consumable

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

            if validate_permission(request.user, permission, consumer):
                utc_now = timezone.now()
                context = {
                    'utc_now': utc_now,
                    'consumer': consumer,
                    'permission': permission,
                    'request': request,
                    'consumables': Consumable.objects.none(),
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

                if consumer and not context['consumables']:
                    #TODO: send a url to recharge this service
                    raise PaymentException(
                        f'You do not have enough credits to access this service: {permission}',
                        slug='not-enough-consumables')

                response = function(*args, **kwargs)

                if consumer and response.status_code < 400:
                    item = context['consumables'].first()

                    #TODO: can consume the resource per hours
                    #TODO: pass it to celery
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
