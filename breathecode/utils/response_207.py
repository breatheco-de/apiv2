from rest_framework import status
from rest_framework.response import Response


def Response207(success=[], failure=[]):
    content = {'success': success, 'failure': failure}

    return Response(content, status=status.HTTP_207_MULTI_STATUS)
