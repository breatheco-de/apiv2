from rest_framework import status
from rest_framework.response import Response


def response_207(success, failure, status_code, detail, success_key='slug', failure_key='slug'):
    failure = list(failure.values(success_key))
    if type(status_code) is not list:
        status_code = [status_code] * len(failure)
    status_code = [{'status_code': s} for s in status_code]

    if type(detail) is not list:
        detail = [detail] * len(failure)
    detail = [{'detail': detail} for detail in detail]

    failure = [{'resources': [d['slug']]} for d in failure]

    for i in range(len(failure)):
        failure[i] = {**failure[i], **detail[i], **status_code[i]}

    content = {'success': [d[success_key] for d in success], 'failure': failure}
    return Response(content, status=status.HTTP_207_MULTI_STATUS)
