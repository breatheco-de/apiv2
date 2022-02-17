import os
from breathecode.authenticate.models import Token
from django.shortcuts import render
from django.http import HttpResponseRedirect

API_URL = os.getenv('API_URL', '')


def render_message(r, msg):
    return render(r, 'message.html', {
        'MESSAGE': msg,
    })


def private_view(func):
    def inner(*args, **kwargs):
        req = args[0]

        url = req.get_full_path()
        token = req.GET.get('token', None)
        if token is None:
            return HttpResponseRedirect(redirect_to=f'{API_URL}/v1/auth/view/login?url=' + url)

        token = Token.get_valid(token)
        if token is None:
            return render_message(req, 'You don\'t have access to this view or the token is invalid')

        # args = args + (token, )
        kwargs['token'] = token
        return func(*args, **kwargs)

    return inner
