from rest_framework import status
from rest_framework.response import Response

__all__ = ['response_207']


def format_response(data, key):
    response = {}

    if 'detail' in data and data['detail']:
        response['detail'] = data['detail']

    if 'status_code' in data:
        response['status_code'] = data['status_code']

    if 'queryset' in data:
        response['resources'] = [{
            'pk': x.pk,
            'display_field': key,
            'display_value': getattr(x, key) if hasattr(x, key) else None,
        } for x in data['queryset']]

    return response


def response_207(responses, display_name):
    alls = [x._get_response_info() for x in responses]

    success = [format_response(x, display_name) for x in alls if x['status_code'] < 400]
    failure = [format_response(x, display_name) for x in alls if x['status_code'] >= 400]

    content = {'success': success, 'failure': failure}
    return Response(content, status=status.HTTP_207_MULTI_STATUS)
