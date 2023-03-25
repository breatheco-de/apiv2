import os, base64
from breathecode.authenticate.models import Token
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit
from django.shortcuts import render
from django.contrib import messages
from rest_framework.exceptions import PermissionDenied
from ..decorators import validate_permission
from django.http import HttpResponseRedirect

__all__ = ['private_view', 'set_query_parameter', 'render_message']


def set_query_parameter(url, param_name, param_value=''):
    """Given a URL, set or replace a query parameter and return the
    modified URL.

    >>> set_query_parameter('http://example.com?foo=bar&biz=baz', 'foo', 'stuff')
    'http://example.com?foo=stuff&biz=baz'

    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)

    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def render_message(r, msg, btn_label=None, btn_url=None, btn_target='_blank', data={}, status=None):
    _data = {'MESSAGE': msg, 'BUTTON': btn_label, 'BUTTON_TARGET': btn_target, 'LINK': btn_url}

    return render(r, 'message.html', {**_data, **data}, status=status)


def private_view(permission=None):

    def decorator(func):

        def inner(*args, **kwargs):
            req = args[0]

            url = req.get_full_path()
            token = req.GET.get('token', None)
            attempt = req.GET.get('attempt', False)

            valid_token = Token.get_valid(token)
            if valid_token is None and 'token' in req.session:
                valid_token = Token.get_valid(req.session['token'])

            try:

                if token is None and valid_token is None:
                    raise PermissionDenied(f'Please login before you can access this view')
                elif valid_token is None:
                    raise PermissionDenied(f'You don\'t have access to this view')

                if permission is not None:
                    if not validate_permission(valid_token.user, permission):
                        raise PermissionDenied(f'You don\'t have permission {permission} to access this view')

            except Exception as e:
                messages.add_message(req, messages.ERROR, str(e))
                return HttpResponseRedirect(redirect_to=f'/v1/auth/view/login?attempt=1&url=' +
                                            str(base64.b64encode(url.encode('utf-8')), 'utf-8'))

            # inject user in request
            args[0].user = valid_token.user

            kwargs['token'] = valid_token
            return func(*args, **kwargs)

        return inner

    return decorator
