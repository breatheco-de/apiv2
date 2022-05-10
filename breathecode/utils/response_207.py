from rest_framework import status
from rest_framework.response import Response


def response_207(success, failure, success_key='slug', failure_key='slug'):
    content = {'success': success, 'failure': failure}

    return Response(content, status=status.HTTP_207_MULTI_STATUS)
