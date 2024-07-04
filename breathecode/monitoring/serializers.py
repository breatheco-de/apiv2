import logging

from django.core.validators import URLValidator
from rest_framework import serializers

from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.actions import subscribe_repository
from breathecode.monitoring.models import RepositorySubscription
from breathecode.monitoring.tasks import async_subscribe_repo, async_unsubscribe_repo
from breathecode.utils import serpy
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

logger = logging.getLogger(__name__)


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CSVDownloadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()


class CSVUploadSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    url = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    created_at = serpy.Field()
    finished_at = serpy.Field()


class RepoSubscriptionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    hook_id = serpy.Field()
    repository = serpy.Field()
    token = serpy.Field()
    updated_at = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    last_call = serpy.Field()
    owner = AcademySmallSerializer()


class RepositorySubscriptionSerializer(serializers.ModelSerializer):
    token = serializers.CharField(read_only=True)
    repository = serializers.CharField(required=False)
    owner = serializers.IntegerField(read_only=True)
    hook_id = serializers.IntegerField(read_only=True)
    last_call = serializers.DateTimeField(read_only=True)
    status_message = serializers.CharField(read_only=True)

    class Meta:
        model = RepositorySubscription
        fields = "__all__"

    def validate(self, data):
        academy_id = self.context["academy"]
        lang = self.context["lang"]

        # If creating
        if self.instance is None:
            if "repository" not in data or data["repository"] == "":
                raise ValidationException(
                    translation(
                        lang,
                        en="You must specify a repository url",
                        es="Debes especificar el URL del repositorio a subscribir",
                        slug="missing-repo",
                    )
                )

            url_validator = URLValidator()
            try:
                url_validator(data["repository"])
                if "github.com" not in data["repository"]:
                    raise serializers.ValidationError("Only GitHub repositories can be subscribed to")
            except serializers.ValidationError as e:
                raise ValidationException(
                    translation(
                        lang,
                        en=str(e),
                        es="La URL del repositorio debe ser valida y apuntar a github.com",
                        slug="invalid-repo-url",
                    )
                )

            subs = RepositorySubscription.objects.filter(owner__id=academy_id, repository=data["repository"]).first()
            # Sabe repo and academy subscription cannot be CREATED twice
            if subs is not None:
                raise ValidationException(
                    translation(
                        lang,
                        en="There is already another subscription for the same repository and owner, make sure you have access?",
                        es="Ya existe una subscripcion para este mismo repositorio y owner, asegurate de tener accesso",
                        slug="duplicated-repo-subscription",
                    )
                )

        # If updating
        if self.instance:
            if (
                "status" in data
                and data["status"] != self.instance.status
                and data["status"] not in ["DISABLED", "OPERATIONAL"]
            ):
                raise ValidationException(
                    translation(
                        lang,
                        en="Repo Subscription status cannot be manually set to " + data["status"],
                        es="El status de esta subscripción no puede asignarse manualmente como " + data["status"],
                        slug="cannot-manually-set-status",
                    )
                )

            if "repository" in data and data["repository"] != self.instance.repository:
                raise ValidationException(
                    translation(
                        lang,
                        en="You cannot update a subscription repository, create a new one instead",
                        es="No puedes modificar el repositorio de una subscripción, crea una nueva subscripción en su lugar",
                        slug="cannot-manually-update-repo",
                    )
                )

        return super().validate(data)

    def create(self, validated_data):
        academy_id = self.context["academy"]
        lang = self.context["lang"]

        settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
        if settings is None:
            raise ValidationException(
                translation(
                    lang,
                    en="Github credentials and settings have not been found for the academy",
                    es="No se han encontrado credenciales y configuración de Github para esta academia",
                    slug="github-settings-not-found",
                )
            )

        instance = super(RepositorySubscriptionSerializer, self).create(
            {
                **validated_data,
                "owner": settings.academy,
            }
        )

        try:
            subscription = subscribe_repository(instance.id, settings)
            if subscription.status != "OPERATIONAL":
                raise Exception(subscription.status_message)
        except Exception as e:
            logger.error(str(e))
            raise ValidationException(
                translation(
                    lang,
                    en=str(e),
                    es="Error al intentar subscribirse al repositorio, revisa la subscripción para mas detalles",
                    slug="github-error",
                )
            )

    def update(self, instance, validated_data):
        if instance.status == "DISABLED" and validated_data["status"] == "OPERATIONAL":
            async_subscribe_repo.delay(instance.id)

        elif instance.status == "OPERATIONAL" and validated_data["status"] == "DISABLED":
            async_unsubscribe_repo.delay(instance.id, force_delete=False)

        return super().update(instance, validated_data)
