import serpy, logging
from django.utils import timezone
from datetime import timedelta
from .models import FormEntry, AcademyAlias, ShortLink
from breathecode.monitoring.actions import test_link
from breathecode.admissions.models import Academy
from rest_framework import serializers
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class ShortlinkSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    destination = serpy.Field()
    hits = serpy.Field()
    private = serpy.Field()
    lastclick_at = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    id = serpy.Field()


class AutomationSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()


class DownloadableSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    destination_url = serpy.Field()
    preview_url = serpy.Field()


class TagSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    tag_type = serpy.Field()
    automation = AutomationSmallSerializer(required=False)


class FormEntrySerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    tags = serpy.Field()
    storage_status = serpy.Field()
    country = serpy.Field()
    lead_type = serpy.Field()
    academy = AcademySmallSerializer(required=False)
    client_comments = serpy.Field(required=False)
    created_at = serpy.Field()


class FormEntrySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    course = serpy.Field()
    phone = serpy.Field()
    location = serpy.Field()
    language = serpy.Field()
    gclid = serpy.Field()
    utm_url = serpy.Field()
    utm_medium = serpy.Field()
    utm_campaign = serpy.Field()
    utm_source = serpy.Field()
    tags = serpy.Field()
    storage_status = serpy.Field()
    country = serpy.Field()
    ac_expected_cohort = serpy.Field()
    lead_type = serpy.Field()
    created_at = serpy.Field()
    user = UserSmallSerializer(required=False)


class PostFormEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormEntry
        exclude = ()

    def create(self, validated_data):

        academy = None
        if 'location' in validated_data:
            alias = AcademyAlias.objects.filter(active_campaign_slug=validated_data['location']).first()
            if alias is not None:
                academy = alias.academy
            else:
                academy = Academy.objects.filter(active_campaign_slug=validated_data['location']).first()

        # copy the validated data just to do small last minute corrections
        data = validated_data.copy()

        # "us" language will become "en" language, its the right lang code
        if 'language' in data and data['language'] == 'us':
            data['language'] = 'en'

        result = super().create({**data, 'academy': academy})
        return result


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortLink
        exclude = ('academy', )

    def validate(self, data):

        link = ShortLink.objects.filter(slug=data['slug']).first()
        if link is not None and self.instance is None and self.instance.id != link.id:
            raise ValidationException(f'Shortlink with slug {data["slug"]} already exists',
                                      slug='shortlink-already-exists')

        status = test_link(data['destination'])
        if status['status_code'] < 200 or status['status_code'] > 299:
            raise ValidationException(f'Destination URL is invalid, returning status {status["status_code"]}')

        academy = Academy.objects.filter(id=self.context['academy']).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy"]} not found',
                                      slug='academy-not-found')

        utc_now = timezone.now()
        days_ago = self.instance.created_at + timedelta(days=1)
        if days_ago < utc_now:
            raise ValidationException(
                f'You cannot update or delete short links that have been created more than 1 day ago, create a new link instead',
                slug='update-days-ago')

        return {**data, 'academy': academy}

    def create(self, validated_data):
        return ShortLink.objects.create(**validated_data)
