from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from breathecode.utils.exceptions import ProgrammingError
from capyc.rest_framework.exceptions import ValidationException

__all__ = ["capable_of", "acapable_of"]


def capable_of(capability=None):

    def decorator(function):

        def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            try:
                if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
                    request = args[0]

                # websocket support
                elif hasattr(args[0], "ws_request"):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError("Missing request information, use this decorator with DRF View")

            academy_id = get_academy_from_capability(kwargs, request, capability)
            if academy_id:
                kwargs["academy_id"] = academy_id
                # add the new kwargs argument to the context to be used by APIViewExtensions
                request.parser_context["kwargs"]["academy_id"] = academy_id
                return function(*args, **kwargs)

        return wrapper

    return decorator


def acapable_of(capability=None):

    def decorator(function):

        async def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            try:
                if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
                    request = args[0]

                # websocket support
                elif hasattr(args[0], "ws_request"):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError("Missing request information, use this decorator with DRF View")

            academy_id = await sync_to_async(get_academy_from_capability)(kwargs, request, capability)
            if academy_id:
                kwargs["academy_id"] = academy_id
                # add the new kwargs argument to the context to be used by APIViewExtensions
                request.parser_context["kwargs"]["academy_id"] = academy_id
                return await function(*args, **kwargs)

        return wrapper

    return decorator


def get_academy_from_capability(kwargs, request, capability):
    from breathecode.authenticate.models import ProfileAcademy

    academy_id = None

    if (
        "academy_id" not in kwargs
        and "Academy" not in request.headers
        and "academy" not in request.headers
        and "academy" not in request.GET
    ):
        raise PermissionDenied("Missing academy_id parameter expected for the endpoint url or 'Academy' header")

    elif "academy_id" in kwargs:
        academy_id = kwargs["academy_id"]

    elif "Academy" in request.headers:
        academy_id = request.headers["Academy"]

    elif "academy" in request.headers:
        academy_id = request.headers["academy"]

    elif "academy" in request.GET:
        academy_id = request.GET["academy"]

    if not str(academy_id).isdigit():
        raise ValidationException(f"Academy ID needs to be an integer: {str(academy_id)}", slug="invalid-academy-id")

    if isinstance(request.user, AnonymousUser):
        raise PermissionDenied("Invalid user")

    capable = ProfileAcademy.objects.filter(
        user=request.user.id, academy__id=academy_id, role__capabilities__slug=capability
    )

    if capable.count() == 0:
        raise PermissionDenied(
            f"You (user: {request.user.id}) don't have this capability: {capability} for academy {academy_id}"
        )

    academy = capable.first().academy
    if academy.status == "DELETED":
        raise PermissionDenied("This academy is deleted")
    if request.get_full_path() != "/v1/admissions/academy/activate" and academy.status == "INACTIVE":
        raise PermissionDenied("This academy is not active")

    return academy_id
