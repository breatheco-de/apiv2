import asyncio
import logging
import traceback
from typing import Any, Optional

from adrf.requests import AsyncRequest
from asgiref.sync import sync_to_async
from capyc.rest_framework.exceptions import PaymentException, ValidationException
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.authenticate.models import Permission, User

from ..exceptions import ProgrammingError

__all__ = ["has_permission", "validate_permission"]

logger = logging.getLogger(__name__)


def validate_permission(user: User, permission: str) -> bool:
    found = Permission.objects.filter(codename=permission).first()
    if not found:
        return False

    return found.user_set.filter(id=user.id).exists() or found.group_set.filter(user__id=user.id).exists()


@sync_to_async
def avalidate_permission(user: User, permission: str) -> bool:
    return validate_permission(user, permission)


# that must be remove from here
def render_message(
    r,
    msg,
    btn_label=None,
    btn_url=None,
    btn_target="_blank",
    data=None,
    status=None,
    go_back=None,
    url_back=None,
    academy=None,
):
    if data is None:
        data = {}

    _data = {
        "MESSAGE": msg,
        "BUTTON": btn_label,
        "BUTTON_TARGET": btn_target,
        "LINK": btn_url,
        "GO_BACK": go_back,
        "URL_BACK": url_back,
    }

    if academy:
        _data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        _data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        _data["COMPANY_LOGO"] = academy.logo_url
        _data["COMPANY_NAME"] = academy.name

        if "heading" not in _data:
            _data["heading"] = academy.name

    return render(r, "message.html", {**_data, **data}, status=status)


def handle_exc(
    format: str,
    request: HttpRequest,
    e: Exception,
    message: Optional[str] = None,
    status: Optional[int] = None,
    use_json_response: bool = False,
) -> Response | HttpResponse | JsonResponse:
    if format == "websocket":
        raise e

    if message is None:
        message = str(e)

    if status is None:
        status = e.status_code if hasattr(e, "status_code") else 400

    if format == "html":
        return render_message(request, message, status=status)

    http_cls = JsonResponse if use_json_response else HttpResponse

    return http_cls({"detail": message, "status_code": status}, status)


def has_permission(permission: str, format="json") -> callable:
    """Check if the current user can access to the resource through of permissions."""

    def decorator(function: callable) -> callable:

        def validate_and_get_request(permission: str, args: Any) -> HttpRequest | AsyncRequest:
            if isinstance(permission, str) == False:
                raise ProgrammingError("Permission must be a string")

            try:
                if hasattr(args[0], "__class__") and isinstance(args[0], APIView):
                    request = args[1]

                elif hasattr(args[0], "user") and hasattr(args[0].user, "has_perm"):
                    request = args[0]

                else:
                    raise IndexError()

            except IndexError:
                raise ProgrammingError("Missing request information, use this decorator with DRF View")

            return request

        def wrapper(*args, **kwargs):
            request = validate_and_get_request(permission, args)

            try:
                if validate_permission(request.user, permission):
                    return function(*args, **kwargs)

                elif isinstance(request.user, AnonymousUser):
                    raise ValidationException(
                        f"Anonymous user don't have this permission: {permission}",
                        code=403,
                        slug="anonymous-user-without-permission",
                    )

                else:
                    raise ValidationException(
                        (f"You (user: {request.user.id}) don't have this permission: " f"{permission}"),
                        code=403,
                        slug="without-permission",
                    )

            except PaymentException as e:
                if format == "websocket":
                    raise e

                if format == "html":
                    return render_message(
                        request,
                        str(e),
                        status=402,
                        go_back="Go back to Dashboard",
                        url_back="https://4geeks.com/choose-program",
                    )

                return Response({"detail": str(e), "status_code": 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == "websocket":
                    raise e

                status = e.status_code if hasattr(e, "status_code") else 400

                if format == "html":
                    return render_message(request, str(e), status=status)

                return Response({"detail": str(e), "status_code": status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == "html":
                    return render_message(request, "unexpected error, contact admin if you are affected", status=500)

                response = JsonResponse({"detail": str(e), "status_code": 500})
                response.status_code = 500
                return response

        @sync_to_async
        def async_get_user(request: AsyncRequest) -> User:
            return request.user

        async def async_wrapper(*args, **kwargs):
            request = validate_and_get_request(permission, args)

            try:
                user = await async_get_user(request)
                if await avalidate_permission(user, permission):
                    return await function(*args, **kwargs)

                elif isinstance(user, AnonymousUser):
                    raise ValidationException(
                        f"Anonymous user don't have this permission: {permission}",
                        code=403,
                        slug="anonymous-user-without-permission",
                    )

                else:
                    raise ValidationException(
                        (f"You (user: {user.id}) don't have this permission: " f"{permission}"),
                        code=403,
                        slug="without-permission",
                    )

            except PaymentException as e:
                if format == "websocket":
                    raise e

                if format == "html":
                    return render_message(
                        request,
                        str(e),
                        status=402,
                        go_back="Go back to Dashboard",
                        url_back="https://4geeks.com/choose-program",
                    )

                return Response({"detail": str(e), "status_code": 402}, 402)

            # handle html views errors
            except ValidationException as e:
                if format == "websocket":
                    raise e

                status = e.status_code if hasattr(e, "status_code") else 400

                if format == "html":
                    return render_message(request, str(e), status=status)

                return Response({"detail": str(e), "status_code": status}, status)

            # handle html views errors
            except Exception as e:
                # show stacktrace for unexpected exceptions
                traceback.print_exc()

                if format == "html":
                    return render_message(request, "unexpected error, contact admin if you are affected", status=500)

                response = JsonResponse({"detail": str(e), "status_code": 500})
                response.status_code = 500
                return response

        if asyncio.iscoroutinefunction(function):
            return async_wrapper

        return wrapper

    return decorator
