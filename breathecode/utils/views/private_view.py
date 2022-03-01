import os, base64
from breathecode.authenticate.models import Token
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit
from django.shortcuts import render
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
    print(new_query_string, 'new_query_string')

    return urlunsplit((scheme, netloc, path, new_query_string, fragment))


def render_message(r, msg, btn_label=None, btn_url=None, btn_target='_blank', data=None):
    _data = {'MESSAGE': msg, 'BUTTON': btn_label, 'BUTTON_TARGET': btn_target, 'LINK': btn_url}

    return render(r, 'message.html', {**_data, **data})


def private_view(func):
    def inner(*args, **kwargs):
        req = args[0]

        url = req.get_full_path()
        token = req.GET.get('token', None)
        valid_token = Token.get_valid(token)
        attempt = req.GET.get('attempt', False)
        if token is None or (valid_token is None and attempt == False):
            return HttpResponseRedirect(redirect_to=f'/v1/auth/view/login?attempt=1&url=' +
                                        str(base64.b64encode(url.encode('utf-8')), 'utf-8'))

        if valid_token is None:
            return render_message(req, f'You don\'t have access to this view or the token is invalid {token}')

        print('token', valid_token)

        kwargs['token'] = valid_token
        return func(*args, **kwargs)

    return inner
