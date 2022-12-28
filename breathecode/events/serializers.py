from typing import Any
from breathecode.marketing.actions import validate_marketing_tags
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException
from .models import Event, EventType, Organization, EventbriteWebhook
from slugify import slugify
from rest_framework import serializers
import serpy, logging

logger = logging.getLogger(__name__)


class CitySerializer(serpy.Serializer):
    name = serpy.Field()


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class AcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    city = CitySerializer(required=False)


class EventTypeSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class EventTypeSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    academy = AcademySerializer(required=False)


class AcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class SyllabusSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CohortSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class EventTypeVisibilitySettingSerializer(serpy.Serializer):
    id = serpy.Field()
    cohort = CohortSmallSerializer(required=False)
    syllabus = SyllabusSmallSerializer(required=False)
    academy = AcademySmallSerializer(required=False)


class VenueSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    street_address = serpy.Field()
    city = serpy.Field()
    zip_code = serpy.Field()
    state = serpy.Field()
    updated_at = serpy.Field()


class OrganizationBigSerializer(serpy.Serializer):
    id = serpy.Field()
    eventbrite_id = serpy.Field()
    eventbrite_key = serpy.Field()
    name = serpy.Field()
    sync_status = serpy.Field()
    sync_desc = serpy.Field()
    updated_at = serpy.Field()
    created_at = serpy.Field()


class OrganizationSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    sync_status = serpy.Field()
    sync_desc = serpy.Field()


class OrganizerSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    eventbrite_id = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    organization = OrganizationSmallSerializer()
    academy = AcademySerializer(required=False)
    updated_at = serpy.Field()
    created_at = serpy.Field()


class EventTinySerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)


class EventSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    excerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    description = serpy.Field()
    capacity = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    status = serpy.Field()
    host = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)
    academy = AcademySerializer(required=False)
    sync_with_eventbrite = serpy.Field()
    eventbrite_sync_status = serpy.Field()
    eventbrite_sync_description = serpy.Field()
    tags = serpy.Field()


class EventSmallSerializerNoAcademy(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    excerpt = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    host = serpy.Field()
    status = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)
    sync_with_eventbrite = serpy.Field()
    eventbrite_sync_status = serpy.Field()
    eventbrite_sync_description = serpy.Field()
    tags = serpy.Field()


class EventCheckinSerializer(serpy.Serializer):
    id = serpy.Field()
    email = serpy.Field()
    status = serpy.Field()
    created_at = serpy.Field()
    attended_at = serpy.Field()
    attendee = UserSerializer(required=False)
    event = EventTinySerializer()


class EventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        exclude = ()

    def validate(self, data: dict[str, Any]):
        lang = data.get('lang', 'en')

        academy = self.context.get('academy_id')

        if ('sync_with_eventbrite' not in data or data['sync_with_eventbrite']
                == False) and ('url' not in data or data['url'] is None or data['url'] == ''):
            raise ValidationException(
                translation(
                    lang,
                    en='Event URL must not be empty unless it will be synched with Eventbrite',
                    es='La URL del evento no puede estar vacía a menos que se sincronice con Eventbrite',
                    slug='empty-url'))

        if 'tags' not in data or data['tags'] == '':
            raise ValidationException(
                translation(lang,
                            en='Event must have at least one tag',
                            es='El evento debe tener al menos un tag',
                            slug='empty-tags'))

        validate_marketing_tags(data['tags'], academy, types=['DISCOVERY'], lang=lang)

        title = data.get('title')
        slug = data.get('slug')

        if slug and self.instance:
            raise ValidationException(
                translation(lang,
                            en='The slug field is readonly',
                            es='El campo slug es de solo lectura',
                            slug='try-update-slug'))

        if title and not slug:
            slug = slugify(data['title']).lower()

        elif slug:
            slug = f'{data["slug"].lower()}'

        existing_events = Event.objects.filter(slug=slug)
        if slug and not self.instance and existing_events.exists():
            raise ValidationException(
                translation(lang,
                            en=f'Event slug {slug} already taken, try a different slug',
                            es=f'El slug {slug} ya está en uso, prueba con otro slug',
                            slug='slug-taken'))

        if 'event_type' in data and 'lang' in data and data['event_type'].academy.lang != data['lang']:
            raise ValidationException(
                translation(lang,
                            en='Event type and event language must match',
                            es='El tipo de evento y el idioma del evento deben coincidir',
                            slug='event-type-lang-mismatch'))

        if 'event_type' in data:
            data['lang'] = data['event_type'].lang

        data['slug'] = slug

        return data

    def create(self, validated_data):
        # hard-code the organizer to the academy organizer
        try:
            validated_data['organizer'] = validated_data['academy'].organizer
        except:
            pass

        return super().create(validated_data)

    def update(self, instance, validated_data):

        # hard-code the organizer to the academy organizer
        try:
            validated_data['organizer'] = validated_data['academy'].organizer
        except:
            pass

        return super().update(instance, validated_data)


class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        exclude = ()


class EventbriteWebhookSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventbriteWebhook
        exclude = ()


class PostEventTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventType
        exclude = ()
