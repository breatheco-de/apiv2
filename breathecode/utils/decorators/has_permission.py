from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView

from breathecode.authenticate.models import Permission, User
from breathecode.payments.models import Consumable, Invoice, Service
from breathecode.payments.signals import consume_service

from ..exceptions import ProgramingError
from ..validation_exception import ValidationException

__all__ = ['has_permission', 'validate_permission']


def validate_permission(user: User, permission: str) -> bool:
    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).exists() or found.group_set.filter(user__id=user.id).exists()


#TODO: check if required_payment is needed
def has_permission(permission: str, consumer: bool = False) -> callable:
    """This decorator check if the current user can access to the resource through of permissions"""

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

            if validate_permission(request.user, permission):
                now = timezone.now()

                response = function(*args, **kwargs)

                if consumer and response.status_code < 400:
                    item = Consumable.objects.filter(Q(valid_until__lte=now) | Q(valid_until=None),
                                                     user=request.user,
                                                     service__groups__permissions__slug=permission).exclude(
                                                         how_many=0).order_by('id').first()

                    #TODO: can consume the resource per hours
                    consume_service.send(instance=item, sender=item.__class__, how_many=1)

                return response

            elif isinstance(request.user, AnonymousUser):
                raise ValidationException(f'Anonymous user don\'t have this permission: {permission}',
                                          code=403,
                                          slug='anonymous-user-without-permission')

            else:

                raise ValidationException((f'You (user: {request.user.id}) don\'t have this permission: '
                                           f'{permission}'),
                                          code=403,
                                          slug='without-permission')

        return wrapper

    return decorator
