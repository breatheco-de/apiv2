from rest_framework.exceptions import PermissionDenied
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import AnonymousUser

from breathecode.utils.exceptions import ProgramingError
from ..validation_exception import ValidationException
from rest_framework.views import APIView

__all__ = ['capable_of']


def capable_of(capability=None):
    def decorator(function):
        def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgramingError('Capability must be a string')

            try:
                if hasattr(args[0], '__class__') and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], 'user') and hasattr(args[0].user, 'has_perm'):
                    request = args[0]

                # websocket support
                elif hasattr(args[0], 'ws_request'):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgramingError('Missing request information, use this decorator with DRF View')

            academy_id = None
            if ('academy_id' not in kwargs and 'Academy' not in request.headers
                    and 'academy' not in request.headers):
                raise PermissionDenied(
                    "Missing academy_id parameter expected for the endpoint url or 'Academy' header")

            elif 'academy_id' in kwargs:
                academy_id = kwargs['academy_id']

            elif 'Academy' in request.headers:
                academy_id = request.headers['Academy']

            elif 'academy' in request.headers:
                academy_id = request.headers['academy']

            if not str(academy_id).isdigit():
                raise ValidationException(f'Academy ID needs to be an integer: {str(academy_id)}',
                                          slug='invalid-academy-id')

            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied('Invalid user')

            capable = ProfileAcademy.objects.filter(user=request.user.id,
                                                    academy__id=academy_id,
                                                    role__capabilities__slug=capability)
            if capable.count() > 0:
                kwargs['academy_id'] = academy_id
                return function(*args, **kwargs)

            raise PermissionDenied(
                f"You (user: {request.user.id}) don't have this capability: {capability} for academy {academy_id}"
            )

        return wrapper

    return decorator
