import serpy
from .models import FormEntry, AcademyAlias
from breathecode.admissions.models import Academy
from rest_framework import serializers


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class AutomationSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()


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
    created_at = serpy.Field()


class FormEntrySmallSerializer(serpy.Serializer):
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
    created_at = serpy.Field()


class PostFormEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormEntry
        exclude = ()

    def create(self, validated_data):

        academy = None
        if "location" in validated_data:
            alias = AcademyAlias.objects.filter(
                active_campaign_slug=validated_data['location']).first()
            if alias is not None:
                academy = alias.academy
            else:
                academy = Academy.objects.filter(
                    active_campaign_slug=validated_data['location']).first()

        result = super().create({**validated_data, "academy": academy})
        return result
