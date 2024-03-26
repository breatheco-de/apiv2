import logging
from breathecode.utils import serpy
from rest_framework import serializers
from breathecode.utils.i18n import translation
from breathecode.monitoring.models import RepositorySubscription
from breathecode.services.github import Github
from breathecode.utils import ValidationException
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.monitoring.actions import subscribe_repository

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
    updated_at = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    owner = AcademySmallSerializer()


class RepositorySubscriptionSerializer(serializers.ModelSerializer):
    token = serializers.CharField(read_only=True)
    owner = serializers.IntegerField(read_only=True)

    class Meta:
        model = RepositorySubscription
        fields = '__all__'

    def validate(self, data):
        academy_id = self.context['academy']
        lang = self.context['lang']

        subs = RepositorySubscription.objects.filter(owner__id=academy_id, repository=data['repository']).first()
        if subs is not None:
            raise ValidationException(
                translation(
                    lang,
                    en=
                    'There is already another subscription for the same repository and owner, make sure you have access?',
                    es='Ya existe una subscripcion para este mismo repositorio y owner, asegurate de tener accesso',
                    slug='duplicated-repo-subscription'))

        return super().validate(data)

    def create(self, validated_data):
        academy_id = self.context['academy']
        lang = self.context['lang']

        settings = AcademyAuthSettings.objects.filter(academy__id=academy_id).first()
        if settings is None:
            raise ValidationException(
                translation(lang,
                            en='Github credentials and settings have not been found for the academy',
                            es='No se han encontrado credenciales y configuración de Github para esta academia',
                            slug='github-settings-not-found'))

        instance = super(RepositorySubscriptionSerializer, self).create({
            **validated_data,
            'owner': settings.academy,
        })

        try:
            subscribe_repository(instance, settings)
        except Exception as e:
            logger.error(str(e))
            raise ValidationException(
                translation(lang,
                            en='Error when connecting with Github to register repo subscription',
                            es='Error al intentar subscribirse al repositorio durante la conexión con Github',
                            slug='github-error'))
