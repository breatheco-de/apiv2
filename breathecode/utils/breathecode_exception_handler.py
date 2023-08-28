from rest_framework.views import exception_handler
from django.core.exceptions import ValidationError
from breathecode.utils.payment_exception import PaymentException

from breathecode.utils.validation_exception import ValidationException

__all__ = ['breathecode_exception_handler']


def get_item_attrs(item):
    data = {
        'pk': item.pk,
    }

    if hasattr(item, 'slug'):
        data['slug'] = item.slug

    if hasattr(item, 'name'):
        data['name'] = item.name

    return data


def breathecode_exception_handler(exc, context):
    # This is to be used with the Django REST Framework (DRF) as its
    # global exception handler.  It replaces the POST data of the Django
    # request with the parsed data from the DRF.  This is necessary
    # because we cannot read the request data/stream more than once.
    # This will allow us to see the parsed POST params in the rollbar
    # exception log.

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    context['request']._request.POST = context['request'].data
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        is_our_exception = isinstance(exc, ValidationException) or isinstance(exc, PaymentException)
        if is_our_exception and isinstance(exc.detail, list):

            items = []

            for x in response.data:
                data = {
                    'detail': str(x),
                    'status_code': x.status_code,
                }

                if x.silent:
                    data['silent'] = True
                    data['silent_code'] = x.slug

                if x.data:
                    data['data'] = x.data

                if x.queryset:
                    data['items'] = [get_item_attrs(v) for v in x.queryset]
                items.append(data)

            if len(items) == 1:
                items = items[0]

            response.data = items

        elif is_our_exception:
            response.data['status_code'] = response.status_code

            if exc.silent:
                response.data['silent'] = True
                response.data['silent_code'] = exc.slug

            if exc.data is not None:
                response.data['data'] = exc.data

            if exc.queryset:
                response.data['items'] = [get_item_attrs(v) for v in exc.queryset]

        elif isinstance(exc, ValidationError):
            response.data['status_code'] = 400

        elif isinstance(response.data, list):
            if response.data[0].code != 'invalid':
                response.data = {'status_code': response.data[0].code, 'details': str(response.data[0])}
            else:
                response.data = {'status_code': 500, 'details': str(response.data[0])}

        else:
            response.data['status_code'] = response.status_code

    return response
