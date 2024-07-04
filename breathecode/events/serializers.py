import logging
from datetime import timedelta
from typing import Any

from django.db.models.query_utils import Q
from django.utils import timezone
from rest_framework import serializers
from slugify import slugify

import breathecode.activity.tasks as tasks_activity
from breathecode.admissions.models import Academy
from breathecode.admissions.serializers import UserPublicSerializer
from breathecode.authenticate.models import Profile, ProfileTranslation
from breathecode.marketing.actions import validate_marketing_tags
from breathecode.registry.models import Asset
from breathecode.registry.serializers import AssetSmallSerializer
from breathecode.utils import serpy
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

from .models import Event, EventbriteWebhook, EventCheckin, EventType, LiveClass, Organization

logger = logging.getLogger(__name__)


class CitySerializer(serpy.Serializer):
    name = serpy.Field()


class UserSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


class ProfileTranslationSerializer(serpy.Serializer):
    bio = serpy.Field()
    lang = serpy.Field()


class ProfileSerializer(serpy.Serializer):
    avatar_url = serpy.Field()
    phone = serpy.Field()

    twitter_username = serpy.Field()
    github_username = serpy.Field()
    portfolio_url = serpy.Field()
    linkedin_url = serpy.Field()

    blog = serpy.Field()
    bio = serpy.Field()

    translations = serpy.MethodField()

    def get_translations(self, obj):
        translations = ProfileTranslation.objects.filter(profile=obj)
        return ProfileTranslationSerializer(translations, many=True).data


class UserBigSerializer(UserSerializer):
    profile = serpy.MethodField()

    def get_profile(self, obj):
        profile = Profile.objects.filter(user=obj).first()

        if not profile:
            return None

        return ProfileSerializer(profile, many=False).data


class AcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    city = CitySerializer(required=False)


class EventTypeSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class EventTypeSerializer(EventTypeSmallSerializer):
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


class EventTypeBigSerializer(EventTypeSerializer):
    icon_url = serpy.Field()
    allow_shared_creation = serpy.Field()
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


class OrganizationSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    sync_status = serpy.Field()
    sync_desc = serpy.Field()


class OrganizationBigSerializer(OrganizationSmallSerializer):
    eventbrite_id = serpy.Field()
    eventbrite_key = serpy.Field()
    updated_at = serpy.Field()
    created_at = serpy.Field()


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


class EventSmallSerializer(EventTinySerializer):
    slug = serpy.Field()
    excerpt = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    description = serpy.Field()
    capacity = serpy.Field()
    status = serpy.Field()
    host = serpy.Field()
    ended_at = serpy.Field()
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)
    academy = AcademySerializer(required=False)
    sync_with_eventbrite = serpy.Field()
    eventbrite_sync_status = serpy.Field()
    eventbrite_sync_description = serpy.Field()
    tags = serpy.Field()
    asset_slug = serpy.Field()
    host_user = UserSerializer(required=False)
    author = UserSerializer(required=False)
    asset = serpy.MethodField()

    def get_asset(self, obj):
        if obj.asset_slug is not None:
            asset = Asset.objects.filter(slug=obj.asset_slug).first()
            if asset is not None:
                return AssetSmallSerializer(asset, many=False).data
        return None


class EventJoinSmallSerializer(EventSmallSerializer):
    live_stream_url = serpy.Field()


class LiveClassJoinSerializer(serpy.Serializer):
    id = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    live_stream_url = serpy.MethodField()
    title = serpy.MethodField()

    def get_live_stream_url(self, obj):
        if obj.cohort_time_slot.cohort.online_meeting_url is not None:
            return obj.cohort_time_slot.cohort.online_meeting_url

        return None

    def get_title(self, obj):
        if obj.cohort_time_slot.cohort.online_meeting_url is not None:
            return obj.cohort_time_slot.cohort.name

        return None


class EventSmallSerializerNoAcademy(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    excerpt = serpy.Field()
    capacity = serpy.Field()
    title = serpy.Field()
    lang = serpy.Field()
    url = serpy.Field()
    banner = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    ended_at = serpy.Field()
    host = serpy.Field()
    asset_slug = serpy.Field()
    status = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    venue = VenueSerializer(required=False)
    sync_with_eventbrite = serpy.Field()
    eventbrite_sync_status = serpy.Field()
    eventbrite_sync_description = serpy.Field()
    tags = serpy.Field()


class EventPublicBigSerializer(EventSmallSerializer):
    currency = serpy.Field()
    host_user = UserBigSerializer(required=False)
    free_for_bootcamps = serpy.Field()
    free_for_all = serpy.Field()
    published_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class EventBigSerializer(EventPublicBigSerializer):
    live_stream_url = serpy.Field()
    organization = OrganizationSmallSerializer(required=False)
    host_user = UserBigSerializer(required=False)
    event_type = EventTypeBigSerializer(required=False)
    eventbrite_id = serpy.Field()
    eventbrite_url = serpy.Field()
    eventbrite_organizer_id = serpy.Field()
    eventbrite_status = serpy.Field()


class AcademyEventSmallSerializer(serpy.Serializer):
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
    ended_at = serpy.Field()
    status = serpy.Field()
    host = serpy.Field()
    event_type = EventTypeSmallSerializer(required=False)
    online_event = serpy.Field()
    live_stream_url = serpy.Field()
    venue = VenueSerializer(required=False)
    academy = AcademySerializer(required=False)
    sync_with_eventbrite = serpy.Field()
    eventbrite_sync_status = serpy.Field()
    eventbrite_sync_description = serpy.Field()
    tags = serpy.Field()
    host_user = UserSerializer(required=False)
    author = UserSerializer(required=False)
    free_for_all = serpy.Field()
    asset = serpy.MethodField()

    def get_asset(self, obj):
        if obj.asset_slug is not None:
            asset = Asset.objects.filter(slug=obj.asset_slug).first()
            if asset is not None:
                return AssetSmallSerializer(asset, many=False).data
        return None


class GetLiveClassSerializer(serpy.Serializer):
    id = serpy.Field()
    hash = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    cohort = serpy.MethodField()

    def get_cohort(self, obj):
        return CohortSmallSerializer(obj.cohort_time_slot.cohort).data


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


class EventHookCheckinSerializer(serpy.Serializer):
    id = serpy.Field()
    email = serpy.Field()
    status = serpy.Field()
    utm_url = serpy.Field()
    utm_source = serpy.Field()
    utm_campaign = serpy.Field()
    utm_medium = serpy.Field()
    created_at = serpy.Field()
    attended_at = serpy.Field()
    attendee = UserSerializer(required=False)
    event = EventJoinSmallSerializer()


class EventSerializer(serializers.ModelSerializer):

    class Meta:
        model = Event
        exclude = ()

    def validate(self, data: dict[str, Any]):
        lang = data.get("lang", "en")

        academy = self.context.get("academy_id")

        if ("tags" not in data and self.instance.tags == "") or ("tags" in data and data["tags"] == ""):
            raise ValidationException(
                translation(
                    lang,
                    en="Event must have at least one tag",
                    es="El evento debe tener al menos un tag",
                    slug="empty-tags",
                )
            )

        validate_marketing_tags(data["tags"], academy, types=["DISCOVERY"], lang=lang)

        title = data.get("title")
        slug = data.get("slug")

        if slug and self.instance:
            raise ValidationException(
                translation(
                    lang, en="The slug field is readonly", es="El campo slug es de solo lectura", slug="try-update-slug"
                )
            )

        if title and not slug:
            slug = slugify(data["title"]).lower()

        elif slug:
            slug = f'{data["slug"].lower()}'

        online_event = data.get("online_event")
        live_stream_url = data.get("live_stream_url")
        if online_event == True and (live_stream_url is None or live_stream_url == ""):
            raise ValidationException(
                translation(
                    lang,
                    en="live_stream_url cannot be empty if the event is online.",
                    es="Si el evento es online, entonces live_stream_url no puede estar vacío.",
                    slug="live-stream-url-empty",
                )
            )

        existing_events = Event.objects.filter(slug=slug)
        if slug and not self.instance and existing_events.exists():
            raise ValidationException(
                translation(
                    lang,
                    en=f"Event slug {slug} already taken, try a different slug",
                    es=f"El slug {slug} ya está en uso, prueba con otro slug",
                    slug="slug-taken",
                )
            )

        if "event_type" not in data or data["event_type"] is None:
            raise ValidationException(
                translation(
                    lang, en="Missing event type", es="Debes especificar un tipo de evento", slug="no-event-type"
                )
            )

        if "lang" in data and data["event_type"].lang != data.get("lang", "en"):
            raise ValidationException(
                translation(
                    lang,
                    en="Event type and event language must match",
                    es="El tipo de evento y el idioma del evento deben coincidir",
                    slug="event-type-lang-mismatch",
                )
            )

        if "event_type" in data:
            data["lang"] = data["event_type"].lang

        if not self.instance:
            data["slug"] = slug

        return data

    def create(self, validated_data):
        # hard-code the organizer to the academy organizer
        try:
            validated_data["organizer"] = validated_data["academy"].organizer
        except Exception:
            pass

        return super().create(validated_data)


class EventPUTSerializer(serializers.ModelSerializer):
    banner = serializers.URLField(required=False)
    tags = serializers.CharField(required=False)
    capacity = serializers.IntegerField(required=False)
    starting_at = serializers.DateTimeField(required=False)
    ending_at = serializers.DateTimeField(required=False)
    online_event = serializers.BooleanField(required=False)
    status = serializers.CharField(required=False)

    class Meta:
        model = Event
        exclude = ()

    def validate(self, data: dict[str, Any]):
        lang = data.get("lang", "en")

        academy = self.context.get("academy_id")

        if "tags" in data:
            if data["tags"] == "":
                raise ValidationException(
                    translation(
                        lang,
                        en="Event must have at least one tag",
                        es="El evento debe tener al menos un tag",
                        slug="empty-tags",
                    )
                )

            validate_marketing_tags(data["tags"], academy, types=["DISCOVERY"], lang=lang)

        title = data.get("title")
        slug = data.get("slug")

        if slug and self.instance:
            raise ValidationException(
                translation(
                    lang, en="The slug field is readonly", es="El campo slug es de solo lectura", slug="try-update-slug"
                )
            )

        if title and not slug:
            slug = slugify(data["title"]).lower()

        elif slug:
            slug = f'{data["slug"].lower()}'

        online_event = data.get("online_event")
        live_stream_url = data.get("live_stream_url")
        if (
            online_event == True
            and (live_stream_url is None or live_stream_url == "")
            and (self.instance.live_stream_url is None or self.instance.live_stream_url == "")
        ):
            raise ValidationException(
                translation(
                    lang,
                    en="live_stream_url cannot be empty if the event is online.",
                    es="Si el evento es online, entonces live_stream_url no puede estar vacío.",
                    slug="live-stream-url-empty",
                )
            )

        existing_events = Event.objects.filter(slug=slug)
        if slug and not self.instance and existing_events.exists():
            raise ValidationException(
                translation(
                    lang,
                    en=f"Event slug {slug} already taken, try a different slug",
                    es=f"El slug {slug} ya está en uso, prueba con otro slug",
                    slug="slug-taken",
                )
            )

        event_type = data["event_type"] if "event_type" in data else self.instance.event_type
        if not event_type:
            raise ValidationException(
                translation(
                    lang, en="Missing event type", es="Debes especificar un tipo de evento", slug="no-event-type"
                )
            )

        if "lang" in data and event_type.lang != data["lang"]:
            raise ValidationException(
                translation(
                    lang,
                    en="Event type and event language must match",
                    es="El tipo de evento y el idioma del evento deben coincidir",
                    slug="event-type-lang-mismatch",
                )
            )

        data["lang"] = event_type.lang

        if not self.instance:
            data["slug"] = slug

        return data

    def update(self, instance, validated_data):

        # hard-code the organizer to the academy organizer
        try:
            validated_data["organizer"] = validated_data["academy"].organizer
        except Exception:
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
        exclude = ("visibility_settings",)

    def validate(self, data: dict[str, Any]):
        academy_id = self.context.get("academy_id")
        data["academy"] = Academy.objects.filter(id=academy_id).get()

        if "visibility_settings" in data:
            del data["visibility_settings"]

        return data


class EventCheckinSmallSerializer(serpy.Serializer):
    status = serpy.Field()
    created_at = serpy.Field()
    attendee = serpy.MethodField()

    def get_attendee(self, obj):
        if obj.attendee is None:
            return None
        return UserPublicSerializer(obj.attendee).data


class PUTEventCheckinSerializer(serializers.ModelSerializer):
    attended_at = serializers.DateTimeField(required=False)

    class Meta:
        model = EventCheckin
        exclude = ("event", "created_at", "updated_at")

    def validate(self, data: dict[str, Any]):
        return data

    def update(self, instance, validated_data):

        new_data = {}
        # if "attended_at" not in data and self.instance.attended_at is None:
        #     new_data['attended_at'] = timezone.now()

        if "attended_at" in validated_data and self.instance.attended_at is None:
            tasks_activity.add_activity.delay(
                self.instance.attendee,
                "event_checkin_assisted",
                related_type="events.EventCheckin",
                related_id=self.instance.id,
            )

        event_checkin = super().update(instance, {**validated_data, **new_data})
        return event_checkin


class POSTEventCheckinSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventCheckin
        exclude = ("created_at", "updated_at", "attended_at", "status")

    def validate(self, data):

        event_checkin = EventCheckin.objects.filter(
            Q(attendee=data["attendee"]) | Q(email=data["email"]), event=data["event"]
        ).first()
        if event_checkin is not None:
            if event_checkin.attendee is None:
                event_checkin.attendee = self.context["user"]
                event_checkin.save()

            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="This user already has an event checkin associated to this event",
                    es="Este usuario ya esta registrado en este evento",
                    slug="user-registered-in-event",
                ),
                code=400,
            )

        return data

    def create(self, validated_data):
        event_checkin = super().create(validated_data)

        tasks_activity.add_activity.delay(
            event_checkin.attendee.id,
            "event_checkin_created",
            related_type="events.EventCheckin",
            related_id=event_checkin.id,
        )

        return event_checkin


class PostEventTypeSerializer(EventTypeSerializerMixin):

    class Meta:
        model = EventType
        exclude = ()

    def create(self, validated_data):
        event_type = super().create(validated_data)

        return event_type


class EventTypePutSerializer(EventTypeSerializerMixin):
    slug = serializers.SlugField(required=False)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    lang = serializers.CharField(required=False)
    icon_url = serializers.URLField(required=True)
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

        if not self.instance and "started_at" in data:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="You cannot start a live class before it has been created.",
                    es="No puedes iniciar una clase en vivo antes de que se haya creado.",
                    slug="started-at-on-creation",
                )
            )

        if self.instance and "started_at" in data and len(data) > 1:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Start the class before you can update any other of its attributes.",
                    es="Inicia la clase antes de poder actualizar cualquiera de sus atributos.",
                    slug="only-started-at",
                )
            )

        if self.instance and "started_at" in data and self.instance.started_at:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="This class has already been started.",
                    es="Esta clase ya ha sido iniciada.",
                    slug="started-at-already-set",
                )
            )

        if (
            self.instance
            and "started_at" in data
            and (
                data["started_at"] < utc_now - timedelta(minutes=2)
                or data["started_at"] > utc_now + timedelta(minutes=2)
            )
        ):
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Started at cannot be so different from the current time.",
                    es="La fecha de inicio no puede ser tan diferente de la hora actual.",
                    slug="started-at-too-different",
                )
            )

    def _validate_ended_at(self, data: dict[str, Any]):
        utc_now = timezone.now()

        if not self.instance and "ended_at" in data:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Ended at cannot be set on creation",
                    es="La fecha de finalización no se puede establecer en la creación",
                    slug="ended-at-on-creation",
                )
            )

        if self.instance and "ended_at" in data and len(data) > 1:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Only ended at can be updated",
                    es="Solo se puede actualizar la fecha de finalización",
                    slug="only-ended-at",
                )
            )

        if self.instance and "ended_at" in data and self.instance.ended_at:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Ended at already set",
                    es="La fecha de finalización ya está establecida",
                    slug="ended-at-already-set",
                )
            )

        if self.instance and "ended_at" in data and not self.instance.started_at:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="You cannot end a live class if it has not yet been started.",
                    es="No puede finalizar una clase en vivo si aún no se ha iniciado.",
                    slug="schedule-must-have-started-at-before-ended-at",
                )
            )

        if self.instance and "ended_at" in data and self.instance.started_at >= data["ended_at"]:
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="The live class cannot have ended before starting.",
                    es="La clase en vivo no puede haber finalizado antes de comenzar.",
                    slug="ended-at-cannot-be-less-than-started-at",
                )
            )

        if (
            self.instance
            and "ended_at" in data
            and (data["ended_at"] < utc_now - timedelta(minutes=2) or data["ended_at"] > utc_now + timedelta(minutes=2))
        ):
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="Ended at at cannot be so different from the current time.",
                    es="La fecha de finalización no puede ser tan diferente de la hora actual.",
                    slug="ended-at-too-different",
                )
            )

    def _validate_cohort(self, data: dict[str, Any]):
        if "cohort" in data and data["cohort"].academy.id != int(self.context["academy_id"]):
            raise ValidationException(
                translation(
                    self.context["lang"],
                    en="This cohort does not belong to any of your academies.",
                    es="Este cohort no pertenece a ninguna de tus academias.",
                    slug="cohort-not-belong-to-academy",
                )
            )

    def validate(self, data: dict[str, Any]):
        self._validate_started_at(data)
        self._validate_ended_at(data)
        self._validate_cohort(data)

        return data
