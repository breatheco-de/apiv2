from django.contrib.auth.models import AnonymousUser
from rest_framework.views import APIView

from ..validation_exception import ValidationException
from ..exceptions import ProgramingError
from breathecode.authenticate.models import Permission, User

__all__ = ['has_permission']


def has_perm(user: User, permission: str) -> bool:
    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).count() or found.group_set.filter(user__id=user.id).count()


def has_permission(permission: str):
    """This decorator check if the current user can access to the resource through of permissions"""
    def decorator(function):
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

            if has_perm(request.user, permission):
                return function(*args, **kwargs)

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
