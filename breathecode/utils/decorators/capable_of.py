from asgiref.sync import sync_to_async
from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from typing import Literal

from breathecode.utils.exceptions import ProgrammingError

__all__ = [
    "capable_of",
    "acapable_of",
    "capable_of_many",
    "acapable_of_many",
    "academy_scope_response_meta",
    "get_academy_from_capability",
    "get_academy_ids_from_capability",
]


def capable_of(capability=None):

    def decorator(function):

        def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            request = _get_request(*args)

            academy_id = get_academy_from_capability(kwargs, request, capability)
            if academy_id:
                kwargs["academy_id"] = academy_id
                # add the new kwargs argument to the context to be used by APIViewExtensions
                request.parser_context.setdefault("kwargs", {})
                request.parser_context["kwargs"]["academy_id"] = academy_id
                return function(*args, **kwargs)

        return wrapper

    return decorator


def acapable_of(capability=None):

    def decorator(function):

        async def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            request = _get_request(*args)

            academy_id = await sync_to_async(get_academy_from_capability)(kwargs, request, capability)
            if academy_id:
                kwargs["academy_id"] = academy_id
                # add the new kwargs argument to the context to be used by APIViewExtensions
                request.parser_context.setdefault("kwargs", {})
                request.parser_context["kwargs"]["academy_id"] = academy_id
                return await function(*args, **kwargs)

        return wrapper

    return decorator


def capable_of_many(capability=None, scope: Literal["strict", "read_aggregate"] = "strict"):
    """
    Resolve academy IDs from URL/header/query and validate capability across them.

    strict:
        Require capability for every requested academy.
    read_aggregate:
        Keep only allowed academies and expose request.academy_scope metadata.
    """

    def decorator(function):

        def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            request = _get_request(*args)

            academy_ids = get_academy_ids_from_capability(kwargs, request, capability, scope=scope)
            if academy_ids:
                kwargs["academy_ids"] = academy_ids
                request.parser_context.setdefault("kwargs", {})
                request.parser_context["kwargs"]["academy_ids"] = academy_ids
                return function(*args, **kwargs)

        return wrapper

    return decorator


def acapable_of_many(capability=None, scope: Literal["strict", "read_aggregate"] = "strict"):
    """Async variant of capable_of_many."""

    def decorator(function):

        async def wrapper(*args, **kwargs):
            if isinstance(capability, str) == False:
                raise ProgrammingError("Capability must be a string")

            request = _get_request(*args)

            academy_ids = await sync_to_async(get_academy_ids_from_capability)(
                kwargs, request, capability, scope=scope
            )
            if academy_ids:
                kwargs["academy_ids"] = academy_ids
                request.parser_context.setdefault("kwargs", {})
                request.parser_context["kwargs"]["academy_ids"] = academy_ids
                return await function(*args, **kwargs)

        return wrapper

    return decorator


def academy_scope_response_meta(request, include_full: bool = False):
    scope = getattr(request, "academy_scope", None)
    if not scope:
        return None

    if include_full is False and scope.get("resolution") == "full":
        return None

    return {"academy_scope": scope}


def _get_request(*args):
    try:
        if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
            return args[1]

        if hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
            return args[0]

        # websocket support
        if hasattr(args[0], "ws_request"):
            return args[0]

        raise IndexError()

    except IndexError:
        raise ProgrammingError("Missing request information, use this decorator with DRF View")


def parse_academy_ids_from_request(kwargs, request):
    academy_value = _get_academy_value_from_request(kwargs, request)

    if isinstance(academy_value, int):
        return [academy_value]

    if isinstance(academy_value, list):
        values = academy_value
    else:
        values = [x.strip() for x in str(academy_value).split(",") if x and x.strip()]

    if len(values) == 0:
        raise PermissionDenied("Missing academy_id parameter expected for the endpoint url or 'Academy' header")

    unique_ids = []
    seen = set()
    for value in values:
        if isinstance(value, int):
            academy_id = value
        elif str(value).isdigit():
            academy_id = int(value)
        else:
            raise ValidationException(f"Academy ID needs to be an integer: {str(value)}", slug="invalid-academy-id")

        if academy_id not in seen:
            seen.add(academy_id)
            unique_ids.append(academy_id)

    return unique_ids


def _get_academy_value_from_request(kwargs, request):
    if (
        "academy_id" not in kwargs
        and "Academy" not in request.headers
        and "academy" not in request.headers
        and "academy" not in request.GET
    ):
        raise PermissionDenied("Missing academy_id parameter expected for the endpoint url or 'Academy' header")

    if "academy_id" in kwargs:
        return kwargs["academy_id"]
    if "Academy" in request.headers:
        return request.headers["Academy"]
    if "academy" in request.headers:
        return request.headers["academy"]
    if "academy" in request.GET:
        return request.GET["academy"]

    raise PermissionDenied("Missing academy_id parameter expected for the endpoint url or 'Academy' header")


def _assert_user_capability_for_academy(academy_id: int, request, capability):
    from breathecode.authenticate.models import ProfileAcademy

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


def get_academy_from_capability(kwargs, request, capability):
    academy_id = _get_academy_value_from_request(kwargs, request)
    if not str(academy_id).isdigit():
        raise ValidationException(f"Academy ID needs to be an integer: {str(academy_id)}", slug="invalid-academy-id")

    academy_id = int(academy_id)
    _assert_user_capability_for_academy(academy_id, request, capability)
    return academy_id


def get_academy_ids_from_capability(kwargs, request, capability, scope: Literal["strict", "read_aggregate"] = "strict"):
    if scope not in {"strict", "read_aggregate"}:
        raise ProgrammingError('Scope must be either "strict" or "read_aggregate"')

    academy_ids = parse_academy_ids_from_request(kwargs, request)

    if scope == "strict":
        for academy_id in academy_ids:
            _assert_user_capability_for_academy(academy_id, request, capability)

        return academy_ids

    # read_aggregate
    if isinstance(request.user, AnonymousUser):
        raise PermissionDenied("Invalid user")

    applied_academy_ids = []
    for academy_id in academy_ids:
        try:
            _assert_user_capability_for_academy(academy_id, request, capability)
            applied_academy_ids.append(academy_id)
        except PermissionDenied:
            continue

    if len(applied_academy_ids) == 0:
        raise PermissionDenied(
            f"You (user: {request.user.id}) don't have this capability: {capability} for requested academies"
        )

    request.academy_scope = {
        "requested_academy_ids": academy_ids,
        "applied_academy_ids": applied_academy_ids,
        "resolution": "full" if len(applied_academy_ids) == len(academy_ids) else "partial",
    }

    return applied_academy_ids
