from datetime import timedelta
from typing import Any
from breathecode.marketing.actions import validate_marketing_tags
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException
from .models import Event, EventType, LiveClass, Organization, EventbriteWebhook, EventCheckin
from slugify import slugify
from rest_framework import serializers
import serpy, logging
from django.utils import timezone

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
    description = serpy.Field()
    lang = serpy.Field()
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


class EventTypeBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    lang = serpy.Field()
    allow_shared_creation = serpy.Field()
    academy = AcademySerializer(required=False)
    visibility_settings = serpy.MethodField()

    def get_visibility_settings(self, obj):
        if obj.visibility_settings is not None:
            return EventTypeVisibilitySettingSerializer(obj.visibility_settings.all(), many=True).data
        return None


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
    live_stream_url = serpy.Field()
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
    live_stream_url = serpy.Field()
    tags = serpy.Field()


class GetLiveClassSerializer(serpy.Serializer):
    id = serpy.Field()
    hash = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()


class GetLiveClassJoinSerializer(GetLiveClassSerializer):
    url = serpy.MethodField()

    def get_url(self, obj):
        return obj.cohort_time_slot.cohort.online_meeting_url


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

        online_event = data.get('online_event')
        live_stream_url = data.get('live_stream_url')
        if online_event == True and (live_stream_url is None or live_stream_url == ''):
            raise ValidationException(
                translation(lang,
                            en=f'live_stream_url cannot be empty if the event is online.',
                            es=f'Si el evento es online, entonces live_stream_url no puede estar vacío.',
                            slug='live-stream-url-empty'))

        existing_events = Event.objects.filter(slug=slug)
        if slug and not self.instance and existing_events.exists():
            raise ValidationException(
                translation(lang,
                            en=f'Event slug {slug} already taken, try a different slug',
                            es=f'El slug {slug} ya está en uso, prueba con otro slug',
                            slug='slug-taken'))

        if 'event_type' in data and 'lang' in data and data['event_type'].lang != data['lang']:
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


class EventTypeSerializerMixin(serializers.ModelSerializer):

    class Meta:
        model = EventType
        exclude = ('visibility_settings', )

    def validate(self, data: dict[str, Any]):

        return data


class PUTEventCheckinSerializer(serializers.ModelSerializer):
    attended_at = serializers.DateTimeField(required=False)

    class Meta:
        model = EventCheckin
        exclude = ('event', 'created_at', 'updated_at', 'attendee')

    def validate(self, data: dict[str, Any]):
        return data

    def update(self, instance, validated_data):

        new_data = {}
        # if "attended_at" not in data and self.instance.attended_at is None:
        #     new_data['attended_at'] = timezone.now()

        event_type = super().update(instance, {**validated_data, **new_data})
        return event_type


class PostEventTypeSerializer(EventTypeSerializerMixin):

    class Meta:
        model = EventType
        exclude = ()

    def create(self, validated_data):
        event_type = EventType.objects.create(**validated_data, **self.context)

        return event_type


class EventTypePutSerializer(EventTypeSerializerMixin):
    slug = serializers.SlugField(required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)
    allow_shared_creation = serializers.BooleanField(required=False)

    def update(self, instance, validated_data):

        event_type = super().update(instance, validated_data)

        return event_type


class LiveClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = LiveClass
        exclude = ()

    def _validate_started_at(self, data: dict[str, Any]):
        utc_now = timezone.now()

        if not self.instance and 'started_at' in data:
            raise ValidationException(
                translation(self.context['lang'],
                            en='You cannot start a live class before it has been created.',
                            es='No puedes iniciar una clase en vivo antes de que se haya creado.',
                            slug='started-at-on-creation'))

        if self.instance and 'started_at' in data and len(data) > 1:
            raise ValidationException(
                translation(self.context['lang'],
                            en='Start the class before you can update any other of its attributes.',
                            es='Inicia la clase antes de poder actualizar cualquiera de sus atributos.',
                            slug='only-started-at'))

        if self.instance and 'started_at' in data and self.instance.started_at:
            raise ValidationException(
                translation(self.context['lang'],
                            en='This class has already been started.',
                            es='Esta clase ya ha sido iniciada.',
                            slug='started-at-already-set'))

        if self.instance and 'started_at' in data and (data['started_at'] < utc_now - timedelta(minutes=2) or
                                                       data['started_at'] > utc_now + timedelta(minutes=2)):
            raise ValidationException(
                translation(self.context['lang'],
                            en='Started at cannot be so different from the current time.',
                            es='La fecha de inicio no puede ser tan diferente de la hora actual.',
                            slug='started-at-too-different'))

    def _validate_ended_at(self, data: dict[str, Any]):
        utc_now = timezone.now()

        if not self.instance and 'ended_at' in data:
            raise ValidationException(
                translation(self.context['lang'],
                            en='Ended at cannot be set on creation',
                            es='La fecha de finalización no se puede establecer en la creación',
                            slug='ended-at-on-creation'))

        if self.instance and 'ended_at' in data and len(data) > 1:
            raise ValidationException(
                translation(self.context['lang'],
                            en='Only ended at can be updated',
                            es='Solo se puede actualizar la fecha de finalización',
                            slug='only-ended-at'))

        if self.instance and 'ended_at' in data and self.instance.ended_at:
            raise ValidationException(
                translation(self.context['lang'],
                            en='Ended at already set',
                            es='La fecha de finalización ya está establecida',
                            slug='ended-at-already-set'))

        if self.instance and 'ended_at' in data and not self.instance.started_at:
            raise ValidationException(
                translation(self.context['lang'],
                            en='You cannot end a live class if it has not yet been started.',
                            es='No puede finalizar una clase en vivo si aún no se ha iniciado.',
                            slug='schedule-must-have-started-at-before-ended-at'))

        if self.instance and 'ended_at' in data and self.instance.started_at >= data['ended_at']:
            raise ValidationException(
                translation(self.context['lang'],
                            en='The live class cannot have ended before starting.',
                            es='La clase en vivo no puede haber finalizado antes de comenzar.',
                            slug='ended-at-cannot-be-less-than-started-at'))

        if self.instance and 'ended_at' in data and (data['ended_at'] < utc_now - timedelta(minutes=2)
                                                     or data['ended_at'] > utc_now + timedelta(minutes=2)):
            raise ValidationException(
                translation(self.context['lang'],
                            en='Ended at at cannot be so different from the current time.',
                            es='La fecha de finalización no puede ser tan diferente de la hora actual.',
                            slug='ended-at-too-different'))

    def _validate_cohort(self, data: dict[str, Any]):
        if 'cohort' in data and data['cohort'].academy.id != int(self.context['academy_id']):
            raise ValidationException(
                translation(self.context['lang'],
                            en='This cohort does not belong to any of your academies.',
                            es='Este cohort no pertenece a ninguna de tus academias.',
                            slug='cohort-not-belong-to-academy'))

    def validate(self, data: dict[str, Any]):
        self._validate_started_at(data)
        self._validate_ended_at(data)
        self._validate_cohort(data)

        return data
