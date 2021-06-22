import logging
import os

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.cypress.actions import clean, load_fixtures, load_roles, reset
from breathecode.utils import ValidationException

logger = logging.getLogger(__name__)


def get_cypress_env():
    return os.getenv('ALLOW_UNSAFE_CYPRESS_APP')


class LoadFixtureView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not get_cypress_env():
            raise ValidationException(
                'Nothing to load',
                slug='is-not-allowed')

        load_fixtures()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class LoadRolesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not get_cypress_env():
            raise ValidationException(
                'Nothing to load',
                slug='is-not-allowed')

        load_roles()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not get_cypress_env():
            raise ValidationException(
                'Nothing to reset',
                slug='is-not-allowed')

        reset()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class CleanView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        if not get_cypress_env():
            raise ValidationException(
                'Nothing to clean',
                slug='is-not-allowed')

        clean()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
