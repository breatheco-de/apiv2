from rest_framework.exceptions import PermissionDenied
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import AnonymousUser
from .validation_exception import ValidationException


def capable_of(capability=None):
    def decorator(function):
        def wrapper(*args, **kwargs):

            if isinstance(capability, str) == False:
                raise Exception("Capability must be a string")

            request = None
            try:
                request = args[1]
            except IndexError:
                raise Exception(
                    "Missing request information, please apply this decorator to view class methods only"
                )

            academy_id = None
            if "academy_id" not in kwargs and ('Academy' not in request.headers
                                               or 'academy'
                                               not in request.headers):
                raise PermissionDenied(
                    "Missing academy_id parameter expected for the endpoint url or 'Academy' header"
                )
            elif "academy_id" in kwargs:
                academy_id = kwargs['academy_id']
            else:
                if 'Academy' in request.headers:
                    academy_id = request.headers['Academy']
                if 'academy' in request.headers:
                    academy_id = request.headers['academy']

            if not str(academy_id).isdigit():
                raise ValidationException(
                    f"Academy ID needs to be an integer: {str(academy_id)}",
                    slug="invalid-academy-id")

            if isinstance(request.user, AnonymousUser):
                raise PermissionDenied("Invalid user")

            capable = ProfileAcademy.objects.filter(
                user=request.user.id,
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
