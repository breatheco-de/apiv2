from adrf.views import APIView
from asgiref.sync import sync_to_async
from capyc.core.i18n import translation
from capyc.rest_framework.exceptions import ValidationException
from django.contrib.auth.models import User
from django.http.request import HttpRequest
from linked_services.django.service import Service
from linked_services.rest_framework.decorators import scope
from linked_services.rest_framework.types import LinkedApp, LinkedHttpRequest, LinkedToken
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from breathecode.authenticate.actions import get_user_language
from breathecode.authenticate.serializers import AppUserSerializer
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions

# Create your views here.


# app/user/:id
class AppUserView(APIView):
    permission_classes = [AllowAny]
    extensions = APIViewExtensions(paginate=True)

    @scope(["read:user"])
    def get(self, request: LinkedHttpRequest, app: LinkedApp, token: LinkedToken, user_id=None):
        handler = self.extensions(request)
        lang = get_user_language(request)

        extra = {}
        if app.require_an_agreement:
            extra["appuseragreement__app__id"] = app.id

        if token.sub:
            user = request.get_user()
            extra["id"] = user.id

        if user_id:
            if "id" in extra and extra["id"] != user_id:
                raise ValidationException(
                    translation(
                        lang,
                        en="This user does not have access to this resource",
                        es="Este usuario no tiene acceso a este recurso",
                    ),
                    code=403,
                    slug="user-with-no-access",
                    silent=True,
                )

            if "id" not in extra:
                extra["id"] = user_id

            user = User.objects.filter(**extra).first()
            if not user:
                raise ValidationException(
                    translation(lang, en="User not found", es="Usuario no encontrado"),
                    code=404,
                    slug="user-not-found",
                    silent=True,
                )

            serializer = AppUserSerializer(user, many=False)
            return Response(serializer.data)

        if not token.sub and (id := request.GET.get("id")):
            extra["id"] = id

        for key in ["email", "username"]:
            if key in request.GET:
                extra[key] = request.GET.get(key)

        # test this path
        items = User.objects.filter(**extra)
        items = handler.queryset(items)
        serializer = AppUserSerializer(items, many=True)

        return handler.response(serializer.data)


class GenericView(APIView):

    @sync_to_async
    def get_user(self):
        return self.request.user

    async def get(self, request: HttpRequest):
        user = await self.get_user()

        params = {}
        for key in request.GET.keys():
            params[key] = request.GET.get(key)

        url = "/endpoint"

        async with Service("rigobot", user.id, proxy=True) as s:
            return await s.get(url, params=params)
