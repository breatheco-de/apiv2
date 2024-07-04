import logging
from collections import OrderedDict

from django.contrib.auth.models import User
from django.db.models import Q

from breathecode.admissions.actions import ImportCohortTimeSlots
from breathecode.assignments.models import Task
from breathecode.assignments.serializers import TaskGETSmallSerializer
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy
from breathecode.utils import localize_query, serializers, serpy
from capyc.rest_framework.exceptions import ValidationException

from .actions import haversine, test_syllabus
from .models import (
    COHORT_STAGE,
    Academy,
    Cohort,
    CohortTimeSlot,
    CohortUser,
    Syllabus,
    SyllabusSchedule,
    SyllabusScheduleTimeSlot,
    SyllabusVersion,
)

logger = logging.getLogger(__name__)


class CountrySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    code = serpy.Field()
    name = serpy.Field()


class GetSyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()
    duration_in_hours = serpy.Field()
    duration_in_days = serpy.Field()
    logo = serpy.Field()


class CitySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    name = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()


class PublicProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    avatar_url = serpy.Field()
    show_tutorial = serpy.Field()
    github_username = serpy.Field()


class GetSmallAcademySerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    white_labeled = serpy.Field()
    icon_url = serpy.Field()
    available_as_saas = serpy.Field()


class GetProfileAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    phone = serpy.Field()


class ProfileAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    academy = GetSmallAcademySerializer()
    role = serpy.MethodField()

    def get_role(self, obj):
        return obj.role.slug


class UserPublicSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = PublicProfileSerializer(required=False)


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    last_login = serpy.Field()
    profile = ProfileSerializer(required=False)


class GetSyllabusScheduleSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    syllabus = serpy.MethodField()

    def get_syllabus(self, obj):
        return obj.syllabus.id if obj.syllabus else None


class GetSmallSyllabusScheduleSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    syllabus = serpy.MethodField()

    def get_syllabus(self, obj):
        return obj.syllabus.id if obj.syllabus else None


class GetTinnyCertificateSerializer(serpy.Serializer):
    duration_in_hours = serpy.Field()


class GithubSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    name = serpy.Field()
    username = serpy.Field()


class GetAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    country = CountrySerializer(required=False)
    city = CitySerializer(required=False)
    logo_url = serpy.Field()
    is_hidden_on_prework = serpy.Field()


class GetAcademyWithStatusSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    country = CountrySerializer(required=False)
    city = CitySerializer(required=False)
    logo_url = serpy.Field()


class GetBigAcademySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    country = CountrySerializer(required=False)
    city = CitySerializer(required=False)
    logo_url = serpy.Field()
    active_campaign_slug = serpy.Field()
    logistical_information = serpy.Field()
    latitude = serpy.Field()
    longitude = serpy.Field()
    marketing_email = serpy.Field()
    street_address = serpy.Field()
    website_url = serpy.Field()
    marketing_phone = serpy.Field()
    twitter_handle = serpy.Field()
    facebook_handle = serpy.Field()
    instagram_handle = serpy.Field()
    github_handle = serpy.Field()
    linkedin_url = serpy.Field()
    youtube_url = serpy.Field()
    is_hidden_on_prework = serpy.Field()


class SyllabusVersionSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    status = serpy.Field()
    slug = serpy.MethodField()
    name = serpy.MethodField()
    syllabus = serpy.MethodField()
    duration_in_hours = serpy.MethodField()
    duration_in_days = serpy.MethodField()
    week_hours = serpy.MethodField()
    github_url = serpy.MethodField()
    logo = serpy.MethodField()
    private = serpy.MethodField()

    def get_slug(self, obj):
        return obj.syllabus.slug if obj.syllabus else None

    def get_name(self, obj):
        return obj.syllabus.name if obj.syllabus else None

    def get_syllabus(self, obj):
        return obj.syllabus.id if obj.syllabus else None

    def get_duration_in_hours(self, obj):
        return obj.syllabus.duration_in_hours if obj.syllabus else None

    def get_duration_in_days(self, obj):
        return obj.syllabus.duration_in_days if obj.syllabus else None

    def get_week_hours(self, obj):
        return obj.syllabus.week_hours if obj.syllabus else None

    def get_logo(self, obj):
        return obj.syllabus.logo if obj.syllabus else None

    def get_private(self, obj):
        return obj.syllabus.private if obj.syllabus else None

    def get_github_url(self, obj):
        return obj.syllabus.github_url if obj.syllabus else None


class GetSyllabusVersionSerializer(serpy.Serializer):
    """The serializer schema definition."""

    json = serpy.Field()
    version = serpy.Field()
    status = serpy.Field()
    change_log_details = serpy.Field()
    updated_at = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()
    academy_owner = serpy.MethodField()
    slug = serpy.MethodField()
    name = serpy.MethodField()
    syllabus = serpy.MethodField()
    main_technologies = serpy.MethodField()
    duration_in_hours = serpy.MethodField()
    duration_in_days = serpy.MethodField()
    week_hours = serpy.MethodField()
    github_url = serpy.MethodField()
    logo = serpy.MethodField()
    private = serpy.MethodField()

    def get_slug(self, obj):
        return obj.syllabus.slug if obj.syllabus else None

    def get_name(self, obj):
        return obj.syllabus.name if obj.syllabus else None

    def get_syllabus(self, obj):
        return obj.syllabus.id if obj.syllabus else None

    def get_main_technologies(self, obj):
        return obj.syllabus.main_technologies if obj.syllabus else None

    def get_academy_owner(self, obj):
        if obj.syllabus is not None and obj.syllabus.academy_owner is not None:
            return GetSmallAcademySerializer(obj.syllabus.academy_owner).data
        return None

    def get_duration_in_hours(self, obj):
        return obj.syllabus.duration_in_hours if obj.syllabus else None

    def get_duration_in_days(self, obj):
        return obj.syllabus.duration_in_days if obj.syllabus else None

    def get_week_hours(self, obj):
        return obj.syllabus.week_hours if obj.syllabus else None

    def get_logo(self, obj):
        return obj.syllabus.logo if obj.syllabus else None

    def get_private(self, obj):
        return obj.syllabus.private if obj.syllabus else None

    def get_github_url(self, obj):
        return obj.syllabus.github_url if obj.syllabus else None


class SmallCohortTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""

    id = serpy.Field()
    starting_at = serpy.DatetimeIntegerField()
    ending_at = serpy.DatetimeIntegerField()
    recurrent = serpy.Field()
    recurrency_type = serpy.Field()


class GetCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    never_ends = serpy.Field()
    remote_available = serpy.Field()
    private = serpy.Field()
    language = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    current_day = serpy.Field()
    current_module = serpy.Field()
    stage = serpy.Field()
    online_meeting_url = serpy.Field()
    timezone = serpy.Field()
    schedule = GetSmallSyllabusScheduleSerializer(required=False)
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetAcademySerializer()
    timeslots = serpy.MethodField()
    is_hidden_on_prework = serpy.Field()
    available_as_saas = serpy.Field()

    def get_timeslots(self, obj):
        timeslots = CohortTimeSlot.objects.filter(cohort__id=obj.id)
        return SmallCohortTimeSlotSerializer(timeslots, many=True).data


class PublicCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    never_ends = serpy.Field()
    private = serpy.Field()
    language = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    remote_available = serpy.Field()
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetAcademySerializer()
    distance = serpy.MethodField()
    timezone = serpy.Field()
    schedule = GetSmallSyllabusScheduleSerializer(required=False)
    timeslots = serpy.ManyToManyField(SmallCohortTimeSlotSerializer(attr="cohorttimeslot_set", many=True))

    def get_distance(self, obj):
        if not obj.latitude or not obj.longitude or not obj.academy.latitude or not obj.academy.longitude:
            return None

        return haversine(obj.longitude, obj.latitude, obj.academy.longitude, obj.academy.latitude)


class GetSmallCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    stage = serpy.Field()
    available_as_saas = serpy.Field()


class GetTeacherAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    user = UserPublicSerializer(required=False)
    status = serpy.Field()
    created_at = serpy.Field()

    role = serpy.MethodField()

    def get_role(self, obj):
        return obj.role.slug

    cohorts = serpy.MethodField()

    def get_cohorts(self, obj):
        if obj.user is None:
            return []

        return GetSmallCohortSerializer(
            Cohort.objects.filter(cohortuser__user__id=obj.user.id, cohortuser__role__in=["TEACHER", "ASSISTANT"])
            .exclude(stage__iexact="DELETED")
            .order_by("-ending_date")
            .all(),
            many=True,
        ).data


class GetMeCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    intro_video = serpy.Field()
    current_day = serpy.Field()
    current_module = serpy.Field()
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetAcademySerializer()
    stage = serpy.Field()
    is_hidden_on_prework = serpy.Field()
    available_as_saas = serpy.Field()


class GetPublicCohortUserSerializer(serpy.Serializer):
    user = UserPublicSerializer()
    role = serpy.Field()


class CohortUserHookSerializer(serpy.Serializer):
    id = serpy.Field()
    user = UserSerializer()
    cohort = GetSmallCohortSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    watching = serpy.Field()
    created_at = serpy.Field()


class CohortHookSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    language = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    intro_video = serpy.Field()
    current_day = serpy.Field()
    current_module = serpy.Field()
    remote_available = serpy.Field()
    online_meeting_url = serpy.Field()
    history_log = serpy.Field()
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetAcademySerializer()
    stage = serpy.Field()
    is_hidden_on_prework = serpy.Field()
    available_as_saas = serpy.Field()


class GetCohortUserSerializer(serpy.Serializer):
    """The serializer schema definition."""

    id = serpy.Field()
    user = UserSerializer()
    cohort = GetSmallCohortSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    watching = serpy.Field()
    created_at = serpy.Field()
    profile_academy = serpy.MethodField()

    def get_profile_academy(self, obj):
        profile = ProfileAcademy.objects.filter(user=obj.user, academy=obj.cohort.academy).first()
        return GetProfileAcademySmallSerializer(profile).data if profile else None


class GetCohortUserTasksSerializer(GetCohortUserSerializer):
    """The serializer schema definition."""

    tasks = serpy.MethodField()

    def get_tasks(self, obj):
        tasks = Task.objects.filter(user=obj.user, cohort=obj.cohort)
        return TaskGETSmallSerializer(tasks, many=True).data


class GETCohortTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""

    id = serpy.Field()
    cohort = serpy.MethodField()
    starting_at = serpy.DatetimeIntegerField()
    ending_at = serpy.DatetimeIntegerField()
    recurrent = serpy.Field()
    recurrency_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_cohort(self, obj):
        return obj.cohort.id


class GETSyllabusScheduleTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""

    id = serpy.Field()
    schedule = serpy.MethodField()
    starting_at = serpy.DatetimeIntegerField()
    ending_at = serpy.DatetimeIntegerField()
    recurrent = serpy.Field()
    recurrency_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_schedule(self, obj):
        return obj.schedule.id if obj.schedule else None


class GETCohortUserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    cohort = GetMeCohortSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    created_at = serpy.Field()


# Create your models here.


class UserMeSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()
    profile = ProfileSerializer(required=False)
    roles = serpy.MethodField()
    cohorts = serpy.MethodField()
    date_joined = serpy.Field()

    def get_github(self, obj):
        github = CredentialsGithub.objects.filter(user=obj.id).first()
        if github is None:
            return None
        return GithubSmallSerializer(github).data

    def get_roles(self, obj):
        roles = ProfileAcademy.objects.filter(user=obj.id)
        return ProfileAcademySmallSerializer(roles, many=True).data

    def get_cohorts(self, obj):
        cohorts = CohortUser.objects.filter(user__id=obj.id).exclude(
            Q(educational_status="DROPPED") | Q(educational_status="SUSPENDED")
        )
        return GETCohortUserSmallSerializer(cohorts, many=True).data


class GetSyllabusSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    main_technologies = serpy.Field()
    github_url = serpy.Field()
    duration_in_hours = serpy.Field()
    duration_in_days = serpy.Field()
    week_hours = serpy.Field()
    logo = serpy.Field()
    private = serpy.Field()
    # academy_owner = serpy.MethodField()
    academy_owner = GetSmallAcademySerializer()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    # def get_academy_owner(self, obj):
    #     return obj.academy_owner.id if obj.academy_owner else None


#        ↓ EDIT SERIALIZERS ↓
class AcademySerializer(serializers.ModelSerializer):
    status_fields = ["status"]
    country = CountrySerializer(required=True)
    city = CitySerializer(required=True)

    class Meta:
        model = Academy
        fields = ["id", "slug", "name", "street_address", "country", "city", "is_hidden_on_prework"]

    def validate(self, data):

        if "slug" in data and data["slug"] != self.instance.slug:
            raise ValidationException("Academy slug cannot be updated")

        return data

    def update(self, instance, validated_data):
        del validated_data["slug"]
        return super().update(instance, validated_data)


class SyllabusPOSTSerializer(serializers.ModelSerializer):

    class Meta:
        model = Syllabus
        fields = ["id", "slug"]


class CohortSerializerMixin(serializers.ModelSerializer):
    status_fields = ["stage"]

    syllabus = serializers.CharField(required=False)
    syllabus_version = serializers.CharField(required=False)
    never_ends = serializers.BooleanField(required=False)

    def validate(self, data):

        kickoff_date = (data["kickoff_date"] if "kickoff_date" in data else None) or (
            self.instance.kickoff_date if self.instance else None
        )

        ending_date = (data["ending_date"] if "ending_date" in data else None) or (
            self.instance.ending_date if self.instance else None
        )

        if kickoff_date and ending_date and kickoff_date > ending_date:
            raise ValidationException(
                "kickoff_date cannot be greather than ending_date", slug="kickoff-date-greather-than-ending-date"
            )

        if "stage" in data:
            possible_stages = [stage_slug for stage_slug, stage_label in COHORT_STAGE]
            if data["stage"] not in possible_stages:
                raise ValidationException(f"Invalid cohort stage {data['stage']}", slug="invalid-cohort-stage")

        if "syllabus" in data:
            strings = data["syllabus"].split(".v")

            if len(strings) != 2:
                raise ValidationException(
                    "Syllabus field marformed(`${syllabus.slug}.v{syllabus_version.version}`)",
                    slug="syllabus-field-marformed",
                )

            [syllabus_slug, syllabus_version_number] = strings

            syllabus_version = None
            if syllabus_version_number == "latest":
                syllabus_version = (
                    SyllabusVersion.objects.filter(
                        Q(syllabus__academy_owner__id=self.context["academy"].id) | Q(syllabus__private=False),
                        syllabus__slug=syllabus_slug,
                    )
                    .filter(status="PUBLISHED")
                    .order_by("-version")
                    .first()
                )
            else:
                syllabus_version = SyllabusVersion.objects.filter(
                    Q(syllabus__private=False) | Q(syllabus__academy_owner__id=self.context["academy"].id),
                    syllabus__slug=syllabus_slug,
                    version=syllabus_version_number,
                ).first()

            if not syllabus_version:
                raise ValidationException(
                    f"Syllabus {syllabus_version} doesn't exist", slug="syllabus-version-not-found"
                )

            if syllabus_version_number == "1":
                raise ValidationException(
                    "Syllabus version 1 is only used for marketing purposes and it cannot be assigned to " "any cohort",
                    slug="assigning-a-syllabus-version-1",
                )

            data["syllabus_version"] = syllabus_version

            if "syllabus" in data:
                del data["syllabus"]

        if "slug" in data:
            cohort = Cohort.objects.filter(slug=data["slug"]).first()
            if cohort is not None and self.instance.slug != data["slug"]:
                raise ValidationException("Slug already exists for another cohort", slug="slug-already-exists")

        if "available_as_saas" not in data or data["available_as_saas"] is None:
            data["available_as_saas"] = self.context["academy"].available_as_saas

        if self.instance:
            never_ends = data["never_ends"] if "never_ends" in data else self.instance.never_ends

            ending_date = data["ending_date"] if "ending_date" in data else self.instance.ending_date

        else:
            never_ends = "never_ends" in data and data["never_ends"]
            ending_date = "ending_date" in data and data["ending_date"]

        if never_ends and ending_date:
            raise ValidationException(
                "A cohort that never ends cannot have ending date", slug="cohort-with-ending-date-and-never-ends"
            )

        if not never_ends and not ending_date:
            raise ValidationException(
                "A cohort most have ending date or it should be marked as ever_ends",
                slug="cohort-without-ending-date-and-never-ends",
            )

        if "language" in data:
            language = data["language"]
            if type(language) == str:
                data["language"] = language.lower()
            else:
                raise ValidationException(f"Language property should be a string not a {type(language)}")

        # if cohort is being activated the online_meeting_url should not be null
        if (
            self.instance is not None
            and (self.instance.online_meeting_url is None or self.instance.online_meeting_url == "")
            and self.instance.remote_available
        ):
            stage = data["stage"] if "stage" in data else self.instance.stage
            if stage in ["STARTED", "FINAL_PROJECT"] and stage != self.instance.stage:
                raise ValidationException(
                    "This cohort has a remote option but no online meeting URL has been specified",
                    slug="remove-without-online-meeting",
                )

        return data


class CohortSerializer(CohortSerializerMixin):
    academy = AcademySerializer(many=False, required=False, read_only=True)
    ending_date = serializers.DateTimeField(required=False, allow_null=True)
    is_hidden_on_prework = serializers.BooleanField(required=False, allow_null=True)

    class Meta:
        model = Cohort
        fields = (
            "id",
            "slug",
            "name",
            "remote_available",
            "kickoff_date",
            "current_day",
            "academy",
            "syllabus",
            "schedule",
            "syllabus_version",
            "ending_date",
            "stage",
            "language",
            "created_at",
            "updated_at",
            "never_ends",
            "online_meeting_url",
            "timezone",
            "is_hidden_on_prework",
            "available_as_saas",
        )

    def create(self, validated_data):
        del self.context["request"]
        cohort = Cohort.objects.create(**validated_data, **self.context)

        if cohort.schedule:
            x = ImportCohortTimeSlots(cohort.id)
            x.clean()
            x.sync()

        return cohort


class CohortPUTSerializer(CohortSerializerMixin):
    # id = serializers.IntegerField(required=True)
    slug = serializers.SlugField(required=False)
    name = serializers.CharField(required=False)
    private = serializers.BooleanField(required=False)
    kickoff_date = serializers.DateTimeField(required=False)
    ending_date = serializers.DateTimeField(required=False, allow_null=True)
    remote_available = serpy.Field(required=False)
    current_day = serializers.IntegerField(required=False)
    current_module = serializers.IntegerField(required=False)
    stage = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    is_hidden_on_prework = serializers.BooleanField(required=False, allow_null=True)

    class Meta:
        model = Cohort
        fields = (
            "id",
            "slug",
            "name",
            "kickoff_date",
            "ending_date",
            "remote_available",
            "current_day",
            "stage",
            "language",
            "syllabus",
            "syllabus_version",
            "schedule",
            "never_ends",
            "private",
            "online_meeting_url",
            "timezone",
            "current_module",
            "is_hidden_on_prework",
            "available_as_saas",
        )

    def update(self, instance, validated_data):
        last_schedule = instance.schedule

        update_timeslots = "schedule" in validated_data and last_schedule != validated_data["schedule"]
        cohort = super().update(instance, validated_data)

        if update_timeslots:
            x = ImportCohortTimeSlots(cohort.id)
            x.clean()
            x.sync()

        return cohort


class UserDJangoRestSerializer(serializers.ModelSerializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    # id = serializers.IntegerField()
    # first_name = serializers.CharField()
    # last_name = serializers.CharField()
    email = serializers.CharField(read_only=True)

    # profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email"]


class CohortUserSerializerMixin(serializers.ModelSerializer):
    status_fields = ["role", "finantial_status", "educational_status"]

    def count_certificates_by_cohort(self, cohort, user_id):
        return CohortUser.objects.filter(
            Q(educational_status="ACTIVE") | Q(educational_status__isnull=True),
            user_id=user_id,
            role="STUDENT",
            cohort__schedule=cohort.schedule,
        ).count()

    def validate(self, data: OrderedDict):
        self.context["index"] += 1
        request = self.context["request"]
        is_post_method = not self.instance

        if isinstance(self.initial_data, list):
            id = self.initial_data[self.context["index"]].get("id")
        else:
            id = self.initial_data.get("id")

        user = data.get("user")
        cohort = data.get("cohort")

        if isinstance(self.instance, CohortUser):
            instance = self.instance

        elif self.instance:
            instance = self.instance.filter(id=id).first()

        else:
            instance = None

        if instance and not user:
            user = instance.user

        if instance and not cohort:
            cohort = instance.cohort

        cohorts = Cohort.objects.filter(id=cohort.id) if cohort else Cohort.objects.none()

        # only from this academy
        cohorts = localize_query(cohorts, request).first()

        if not cohorts:
            logger.debug("Cohort not be found in related academies")
            raise ValidationException("Specified cohort not be found")

        prohibited_stages = ["INACTIVE", "DELETED", "ENDED"]

        if is_post_method and "cohort" in data and data["cohort"].stage in prohibited_stages:

            stage = data["cohort"].stage

            raise ValidationException(
                f"You cannot add a student to a cohort that is {stage}.", slug="adding-student-to-a-closed-cohort"
            )

        if cohort.stage == "DELETED":
            raise ValidationException(
                "cannot add or edit a user to a cohort that has been deleted",
                slug="cohort-with-stage-deleted",
                code=400,
            )

        count_cohort_users = CohortUser.objects.filter(user_id=user.id, cohort_id=cohort.id).count()

        if is_post_method and count_cohort_users:
            raise ValidationException("That user already exists in this cohort")

        if (
            "role" in data
            and data["role"] != "STUDENT"
            and not ProfileAcademy.objects.filter(user_id=user.id, academy__id=cohort.academy.id)
            .exclude(role__slug="student")
            .exists()
        ):
            raise ValidationException("The user must be staff member to this academy before it can be a teacher")

        if is_post_method and cohort.schedule and self.count_certificates_by_cohort(cohort, user.id) > 0:
            raise ValidationException(
                "This student is already in another cohort for the same certificate, please mark him/her hi "
                "educational status on this prior cohort different than ACTIVE before cotinuing"
            )

        role = data.get("role")

        exclude_params = {"id": instance.id} if instance else {}
        if role == "TEACHER" and (
            CohortUser.objects.filter(role=role, cohort_id=cohort.id).exclude(**exclude_params).count()
        ):
            raise ValidationException("There can only be one main instructor in a cohort")

        cohort_user = CohortUser.objects.filter(user__id=user.id, cohort__id=cohort.id).first()

        # move it in the view
        if not is_post_method and not cohort_user:
            raise ValidationException("Cannot find CohortUser")

        watching = data.get("watching") == True
        if watching and cohort_user.educational_status != "ACTIVE":
            raise ValidationException("The student is not active in this cohort", slug="student-not-active")

        is_graduated = (
            data.get("educational_status") or (instance and instance.educational_status or "")
        ) == "GRADUATED"

        is_late = (data.get("finantial_status") or (instance and instance.finantial_status or "")) == "LATE"

        if is_graduated and is_late:
            raise ValidationException("Cannot be marked as `GRADUATED` if its financial " "status is `LATE`")

        tasks_pending = Task.objects.filter(
            user_id=user.id, task_status="PENDING", task_type="PROJECT", cohort__id=cohort.id
        ).exclude(revision_status="IGNORED")

        mandatory_slugs = []
        for task in tasks_pending:
            if "days" in task.cohort.syllabus_version.__dict__["json"]:
                for day in task.cohort.syllabus_version.__dict__["json"]["days"]:
                    for assignment in day["assignments"]:
                        if "mandatory" not in assignment or (
                            "mandatory" in assignment and assignment["mandatory"] == True
                        ):
                            mandatory_slugs.append(assignment["slug"])

        has_tasks = (
            Task.objects.filter(associated_slug__in=mandatory_slugs)
            .exclude(revision_status__in=["APPROVED", "IGNORED"])
            .count()
        )

        if is_graduated and has_tasks:
            raise ValidationException("User has tasks with status pending the educational status cannot be GRADUATED")

        return {**data, "cohort": cohort, "user": user, "id": id}


class CohortUserListSerializer(serializers.ListSerializer):

    def create(self, validated_data):

        books = [CohortUser(**item) for item in validated_data]

        items = CohortUser.objects.bulk_create(books)

        for key in range(0, len(items)):
            item = items[key]
            items[key].id = (
                CohortUser.objects.filter(cohort__id=item.cohort_id, user__id=item.user_id)
                .values_list("id", flat=True)
                .first()
            )

        return items

    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        model_mapping = {model.id: model for model in instance}
        data_mapping = {item["id"]: item for item in validated_data}

        # Perform creations and updates.
        ret = []
        for model_id, data in data_mapping.items():
            book = model_mapping.get(model_id, None)
            if book is None:
                ret.append(self.child.create(data))
            else:
                ret.append(self.child.update(book, data))

        # Perform deletions.
        for model_id, model in model_mapping.items():
            if model_id not in data_mapping:
                model.delete()

        return ret


class CohortUserSerializer(CohortUserSerializerMixin):
    cohort = serializers.PrimaryKeyRelatedField(required=False, queryset=Cohort.objects.filter())
    user = serializers.PrimaryKeyRelatedField(required=False, queryset=User.objects.filter())
    role = serializers.CharField(required=False)

    class Meta:
        model = CohortUser
        fields = ["id", "user", "cohort", "role", "educational_status", "finantial_status"]
        list_serializer_class = CohortUserListSerializer


class CohortTimeSlotSerializer(serializers.ModelSerializer):
    status_fields = ["recurrency_type"]
    starting_at = serializers.IntegerField(write_only=True)
    ending_at = serializers.IntegerField(write_only=True)

    class Meta:
        model = CohortTimeSlot
        fields = ["id", "cohort", "starting_at", "ending_at", "recurrent", "recurrency_type", "timezone"]


class SyllabusScheduleSerializer(serializers.ModelSerializer):
    status_fields = ["schedule_type"]

    class Meta:
        model = SyllabusSchedule
        exclude = ()


class SyllabusSchedulePUTSerializer(serializers.ModelSerializer):
    status_fields = ["schedule_type"]

    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    schedule_type = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    syllabus = serializers.IntegerField(required=False)

    class Meta:
        model = SyllabusSchedule
        exclude = ()


class SyllabusScheduleTimeSlotSerializer(serializers.ModelSerializer):
    status_fields = ["recurrency_type"]
    starting_at = serializers.IntegerField(write_only=True)
    ending_at = serializers.IntegerField(write_only=True)

    class Meta:
        model = SyllabusScheduleTimeSlot
        fields = [
            "id",
            "schedule",
            "starting_at",
            "ending_at",
            "recurrent",
            "recurrency_type",
            "timezone",
        ]


class CohortUserPOSTSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    cohort = serpy.Field()
    user = serpy.Field()


class CohortUserPUTSerializer(CohortUserSerializerMixin):
    cohort = serializers.PrimaryKeyRelatedField(required=False, queryset=Cohort.objects.filter())
    user = serializers.PrimaryKeyRelatedField(required=False, queryset=User.objects.filter())

    class Meta:
        model = CohortUser
        fields = ["id", "user", "cohort", "role", "educational_status", "finantial_status", "watching"]
        list_serializer_class = CohortUserListSerializer


class SyllabusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Syllabus
        fields = [
            "id",
            "slug",
            "name",
            "academy_owner",
            "duration_in_days",
            "duration_in_hours",
            "week_hours",
            "github_url",
            "logo",
            "private",
        ]
        exclude = ()


class SyllabusVersionSerializer(serializers.ModelSerializer):
    json = serializers.JSONField()

    class Meta:
        model = SyllabusVersion
        fields = ["json", "version", "syllabus", "status", "change_log_details"]
        exclude = ()
        extra_kwargs = {
            "syllabus": {"read_only": True},
            "version": {"read_only": True},
        }

    def validate(self, data):
        request = self.context["request"]

        _data = super().validate(data)
        if "json" in data:
            try:
                ignore = request.GET.get("ignore", "")
                _log = test_syllabus(data["json"], ignore=ignore.lower().split(","))
                if _log.http_status() != 200:
                    raise ValidationException(
                        f"There are {len(_log.errors)} errors in your syllabus, please validate before submitting",
                        slug="syllabus-with-errors",
                    )
            except Exception as e:
                raise ValidationException(f"Error when testing the syllabus: {str(e)}", slug="syllabus-with-errors")

        return _data

    def create(self, validated_data):
        syllabus = self.context["syllabus"]

        previous_syllabus = SyllabusVersion.objects.filter(syllabus=syllabus).order_by("-version").first()

        version = 1
        if previous_syllabus is not None:
            version = previous_syllabus.version + 1

        return super(SyllabusVersionSerializer, self).create(
            {
                **validated_data,
                "syllabus": syllabus,
                "version": version,
            }
        )


class SyllabusVersionPutSerializer(serializers.ModelSerializer):
    json = serializers.JSONField(required=False)
    status = serializers.CharField(required=False)

    class Meta:
        model = SyllabusVersion
        fields = ["json", "version", "syllabus", "status"]
        exclude = ()
        extra_kwargs = {
            "syllabus": {"read_only": True},
            "version": {"read_only": True},
        }

    def validate(self, data):
        request = self.context["request"]

        _data = super().validate(data)
        if "json" in data:
            try:
                ignore = request.GET.get("ignore", "")
                _log = test_syllabus(data["json"], ignore=ignore.lower().split(","))
                if _log.http_status() != 200:
                    raise ValidationException(
                        f"There are {len(_log.errors)} errors in your syllabus, please validate before submitting",
                        slug="syllabus-with-errors",
                    )
            except Exception as e:
                raise ValidationException(f"Error when testing the syllabus: {str(e)}", slug="syllabus-with-errors")

        return _data


class AcademyReportSerializer(serpy.Serializer):
    """The serializer schema definition."""

    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    logo_url = serpy.Field()
    website_url = serpy.Field()
    street_address = serpy.Field()
    latitude = serpy.Field()
    longitude = serpy.Field()
    status = serpy.Field()

    students = serpy.MethodField()

    def get_students(self, obj):

        query = CohortUser.objects.filter(cohort__academy__id=obj.id, role="STUDENT")
        return {
            "total": query.count(),
            "active": query.filter(educational_status="ACTIVE").count(),
            "suspended": query.filter(educational_status="SUSPENDED").count(),
            "graduated": query.filter(educational_status="GRADUATED").count(),
            "dropped": query.filter(educational_status="DROPPED").count(),
        }

    teachers = serpy.MethodField()

    def get_teachers(self, obj):

        query = CohortUser.objects.filter(cohort__academy__id=obj.id, cohort__stage__in=["STARTED", "FINAL_PROJECT"])
        active = {
            "main": query.filter(role="TEACHER").count(),
            "assistant": query.filter(role="ASSISTANT").count(),
            "reviewer": query.filter(role="REVIEWER").count(),
        }
        active["total"] = int(active["main"]) + int(active["assistant"]) + int(active["reviewer"])

        total = ProfileAcademy.objects.filter(role__slug__in=["teacher", "assistant"])
        return {
            "total": total.count(),
            "active": active,
        }
