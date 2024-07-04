import logging
import os

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.cypress.actions import clean, clean_model, generate_models, load_roles
from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)


def get_cypress_env():
    return os.getenv("ALLOW_UNSAFE_CYPRESS_APP")


class LoadRolesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not get_cypress_env():
            raise ValidationException("Nothing to load", slug="is-not-allowed")

        load_roles()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CleanView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, model_name=None):
        if not get_cypress_env():
            raise ValidationException("Nothing to clean", slug="is-not-allowed")

        if model_name:
            try:
                clean_model(model_name)
            except Exception as e:
                error = str(e)
                slug = "model-not-exits"

                logger.error(error)

                if error.startswith("Exist many app with the same model name"):
                    slug = "many-models-with-the-same-name"

                elif error == "Bad model name format":
                    slug = "bad-model-name-format"

                raise ValidationException(error, code=404, slug=slug)

            return Response(None, status=status.HTTP_204_NO_CONTENT)

        clean()
        return Response(None, status=status.HTTP_204_NO_CONTENT)


class MixerView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not get_cypress_env():
            raise ValidationException("Nothing to load", slug="is-not-allowed")

        if not request.data:
            raise ValidationException("Empty request", slug="is-empty")

        data = request.data

        if not isinstance(data, list):
            data = [data]

        result = generate_models(data)

        return Response(result, status=status.HTTP_200_OK)
