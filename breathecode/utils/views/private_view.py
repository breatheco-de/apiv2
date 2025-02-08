import base64
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django import shortcuts
from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from rest_framework.exceptions import PermissionDenied

from breathecode.authenticate.models import Academy, Token

from ..decorators import validate_permission

__all__ = ["private_view", "set_query_parameter", "render_message"]


def set_query_parameter(url, param_name, param_value=""):
    """Given a URL, set or replace a query parameter and return the modified URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'
    """

    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def render_message(
    r: HttpRequest,
    msg: str,
    btn_label: Optional[str] = None,
    btn_url: Optional[str] = None,
    btn_target: Optional[str] = "_blank",
    data: Optional[dict[str, Any]] = None,
    status: Optional[int] = None,
    academy: Optional[Academy] = None,
):
    if data is None:
        data = {}

    _data = {"MESSAGE": msg, "BUTTON": btn_label, "BUTTON_TARGET": btn_target, "LINK": btn_url}

    if academy:
        _data["COMPANY_INFO_EMAIL"] = academy.feedback_email
        _data["COMPANY_LEGAL_NAME"] = academy.legal_name or academy.name
        _data["COMPANY_LOGO"] = academy.logo_url
        _data["COMPANY_NAME"] = academy.name

        if "heading" not in data:
            _data["heading"] = academy.name

    return shortcuts.render(r, "message.html", {**_data, **data}, status=status)


def private_view(permission=None, auth_url="/v1/auth/view/login", capability=None):

    from ..decorators.capable_of import get_academy_from_capability

    def decorator(func):

        def inner(*args, **kwargs):
            req = args[0]
            url = req.get_full_path()
            token = req.GET.get("token", None)

            if token is not None:
                valid_token = Token.get_valid(token)

            elif "token" in req.session:
                valid_token = Token.get_valid(req.session["token"])

            else:
                valid_token = None

            try:

                if token is None and valid_token is None:
                    raise PermissionDenied("Please login before you can access this view")

                if valid_token is None:
                    raise PermissionDenied("You don't have access to this view")

            except Exception as e:
                messages.add_message(req, messages.ERROR, str(e))
                return HttpResponseRedirect(
                    redirect_to=f"{auth_url}?attempt=1&url=" + str(base64.b64encode(url.encode("utf-8")), "utf-8")
                )

            if permission and validate_permission(valid_token.user, permission) is False:
                return render_message(req, f"You don't have permission {permission} to access this view", status=403)

            if capability:
                try:
                    req.user = valid_token.user
                    academy_id = get_academy_from_capability(kwargs, req, capability)
                    kwargs["academy_id"] = academy_id
                    req.parser_context["kwargs"]["academy_id"] = academy_id

                except Exception as e:
                    # improve this exception handler
                    return render_message(req, str(e), status=403)

            # inject user in request
            args[0].user = valid_token.user

            kwargs["token"] = valid_token
            return func(*args, **kwargs)

        return inner

    return decorator
