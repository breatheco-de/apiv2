import logging
import serpy
from breathecode.admissions.actions import ImportCohortTimeSlots
from django.db.models import Q
from breathecode.assignments.models import Task
from breathecode.utils import ValidationException, localize_query, SerpyExtensions
from rest_framework import serializers
from django.contrib.auth.models import User
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy
from .models import (Academy, SyllabusScheduleTimeSlot, Cohort, SyllabusSchedule, CohortTimeSlot, CohortUser,
                     Syllabus, SyllabusVersion, COHORT_STAGE)

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


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
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
    starting_at = SerpyExtensions.DatetimeIntegerField()
    ending_at = SerpyExtensions.DatetimeIntegerField()
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
    schedule = GetSmallSyllabusScheduleSerializer(required=False)
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetAcademySerializer()


class GetSmallCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    stage = serpy.Field()


class GetMeCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    current_day = serpy.Field()
    current_module = serpy.Field()
    syllabus_version = SyllabusVersionSmallSerializer(required=False)
    academy = GetSmallAcademySerializer()
    stage = serpy.Field()


class GetCohortUserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.Field()
    user = UserSerializer()
    cohort = GetSmallCohortSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    created_at = serpy.Field()
    profile_academy = serpy.MethodField()

    def get_profile_academy(self, obj):
        profile = ProfileAcademy.objects.filter(user=obj.user, academy=obj.cohort.academy).first()
        return GetProfileAcademySmallSerializer(profile).data if profile else None


class GETCohortTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.Field()
    cohort = serpy.MethodField()
    starting_at = SerpyExtensions.DatetimeIntegerField()
    ending_at = SerpyExtensions.DatetimeIntegerField()
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
    starting_at = SerpyExtensions.DatetimeIntegerField()
    ending_at = SerpyExtensions.DatetimeIntegerField()
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
        cohorts = CohortUser.objects.filter(user__id=obj.id)
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
    country = CountrySerializer(required=True)
    city = CitySerializer(required=True)

    class Meta:
        model = Academy
        fields = ['id', 'slug', 'name', 'street_address', 'country', 'city']

    def validate(self, data):

        if 'slug' in data and data['slug'] != self.instance.slug:
            raise ValidationException('Academy slug cannot be updated')

        return data

    def update(self, instance, validated_data):
        del validated_data['slug']
        return super().update(instance, validated_data)


class SyllabusPOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        fields = ['id', 'slug']


class CohortSerializerMixin(serializers.ModelSerializer):
    syllabus = serializers.CharField(required=False)
    syllabus_version = serializers.CharField(required=False)

    def validate(self, data):

        kickoff_date = (data['kickoff_date'] if 'kickoff_date' in data else
                        None) or (self.instance.kickoff_date if self.instance else None)

        ending_date = (data['ending_date'] if 'ending_date' in data else None) or (self.instance.ending_date
                                                                                   if self.instance else None)

        if kickoff_date and ending_date and kickoff_date > ending_date:
            raise ValidationException('kickoff_date cannot be greather than ending_date',
                                      slug='kickoff-date-greather-than-ending-date')

        if 'stage' in data:
            possible_stages = [stage_slug for stage_slug, stage_label in COHORT_STAGE]
            if data['stage'] not in possible_stages:
                raise ValidationException(f"Invalid cohort stage {data['stage']}",
                                          slug='invalid-cohort-stage')

        if 'syllabus' in data:
            strings = data['syllabus'].split('.v')

            if len(strings) != 2:
                raise ValidationException(
                    'Syllabus field marformed(`${syllabus.slug}.v{syllabus_version.version}`)',
                    slug='syllabus-field-marformed')

            [syllabus_slug, syllabus_version_number] = strings

            syllabus_version = SyllabusVersion.objects.filter(
                Q(syllabus__private=False) | Q(syllabus__academy_owner__id=self.context['academy'].id),
                syllabus__slug=syllabus_slug,
                version=syllabus_version_number).first()

            if not syllabus_version:
                raise ValidationException('Syllabus doesn\'t exist', slug='syllabus-version-not-found')

            if syllabus_version_number == '1':
                raise ValidationException(
                    'Syllabus version 1 is only used for marketing purposes and it cannot be assigned to '
                    'any cohort',
                    slug='assigning-a-syllabus-version-1')

            data['syllabus_version'] = syllabus_version

            if 'syllabus' in data:
                del data['syllabus']

        if 'slug' in data:
            cohort = Cohort.objects.filter(slug=data['slug']).first()
            if cohort is not None and self.instance.slug != data['slug']:
                raise ValidationException('Slug already exists for another cohort',
                                          slug='slug-already-exists')

        if self.instance:
            never_ends = (data['never_ends'] if 'never_ends' in data else self.instance.never_ends)

            ending_date = (data['ending_date'] if 'ending_date' in data else self.instance.ending_date)

        else:
            never_ends = 'never_ends' in data and data['never_ends']
            ending_date = 'ending_date' in data and data['ending_date']

        if never_ends and ending_date:
            raise ValidationException('A cohort that never ends cannot have ending date',
                                      slug='cohort-with-ending-date-and-never-ends')

        if not never_ends and not ending_date:
            raise ValidationException('A cohort most have ending date or it should be marked as ever_ends',
                                      slug='cohort-without-ending-date-and-never-ends')

        # if cohort is being activated the online_meeting_url should not be null
        if self.instance is not None and (self.instance.online_meeting_url is None
                                          or self.instance.online_meeting_url
                                          == '') and self.instance.remote_available:
            stage = (data['stage'] if 'stage' in data else self.instance.stage)
            if stage in ['STARTED', 'FINAL_PROJECT'] and stage != self.instance.stage:
                raise ValidationException(
                    'This cohort has a remote option but no online meeting URL has been specified',
                    slug='remove-without-online-meeting')

        return data


class CohortSerializer(CohortSerializerMixin):
    academy = AcademySerializer(many=False, required=False, read_only=True)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'remote_available', 'kickoff_date', 'current_day', 'academy',
                  'syllabus', 'schedule', 'syllabus_version', 'ending_date', 'stage', 'language',
                  'created_at', 'updated_at', 'never_ends', 'online_meeting_url', 'timezone')

    def create(self, validated_data):
        del self.context['request']
        cohort = Cohort.objects.create(**validated_data, **self.context)

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
    current_day = serializers.IntegerField(required=False)
    current_module = serializers.IntegerField(required=False)
    stage = serializers.CharField(required=False)
    language = serializers.CharField(required=False)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date', 'ending_date', 'current_day', 'stage', 'language',
                  'syllabus', 'syllabus_version', 'schedule', 'never_ends', 'private', 'online_meeting_url',
                  'timezone', 'current_module')

    def update(self, instance, validated_data):
        last_schedule = instance.schedule

        update_timeslots = 'schedule' in validated_data and last_schedule != validated_data['schedule']
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
        fields = ['id', 'first_name', 'last_name', 'email']
        # fields = ['id', 'user']


class CohortUserSerializerMixin(serializers.ModelSerializer):
    index = -1

    def count_certificates_by_cohort(self, cohort, user_id):
        return CohortUser.objects.filter(Q(educational_status='ACTIVE') | Q(educational_status__isnull=True),
                                         user_id=user_id,
                                         role='STUDENT',
                                         cohort__schedule=cohort.schedule).count()

    def validate_just_one(self):
        pass

    def validate(self, data):
        self.index = self.index + 1

        request = self.context['request']
        is_many = isinstance(request.data, list)
        cohort_id = self.context['cohort_id']
        user_id = self.context['user_id']
        body = request.data if is_many else [request.data]
        request_item = body[self.index]
        is_post_method = request.method == 'POST'

        id = None
        if is_many and 'id' in request_item:
            id = request_item['id']

        if is_many and 'user' in request_item:
            user_id = request_item['user']

        if is_many and 'cohort' in request_item:
            cohort_id = request_item['cohort']

        if id and (not user_id or not cohort_id):
            ids = CohortUser.objects.filter(id=id).values_list('user_id', 'cohort_id').first()

            if not ids:
                raise ValidationException('Invalid id', code=400)
            user_id = ids[0]
            cohort_id = ids[1]

        if user_id is None:
            user_id = request_item.get('user')

        if not is_many and (cohort_id is None or user_id is None):
            raise ValidationException('Missing cohort_id or user_id', code=400)

        if User.objects.filter(id=user_id).count() == 0:
            raise ValidationException('invalid user_id', code=400)

        cohort = Cohort.objects.filter(id=cohort_id)
        if not cohort:
            raise ValidationException('invalid cohort_id', code=400)

        # only from this academy
        cohort = localize_query(cohort, request).first()

        if cohort is None:
            logger.debug(f'Cohort not be found in related academies')
            raise ValidationException('Specified cohort not be found')

        if cohort.stage == 'DELETED':
            raise ValidationException('cannot add or edit a user to a cohort that has been deleted',
                                      slug='cohort-with-stage-deleted',
                                      code=400)

        count_cohort_users = CohortUser.objects.filter(user_id=user_id, cohort_id=cohort_id).count()

        if is_post_method and count_cohort_users:
            raise ValidationException('That user already exists in this cohort')

        if ('role' in request_item and request_item['role'] != 'STUDENT'
                and not ProfileAcademy.objects.filter(
                    user_id=user_id, academy__id=cohort.academy.id).exclude(role__slug='student').exists()):
            raise ValidationException(
                'The user must be staff member to this academy before it can be a teacher')

        if (is_post_method and cohort.schedule and self.count_certificates_by_cohort(cohort, user_id) > 0):
            raise ValidationException(
                'This student is already in another cohort for the same certificate, please mark him/her hi '
                'educational status on this prior cohort different than ACTIVE before cotinuing')

        role = request_item.get('role')
        if role == 'TEACHER' and CohortUser.objects.filter(
                role=role, cohort_id=cohort_id).exclude(user__id__in=[user_id]).count():
            raise ValidationException('There can only be one main instructor in a cohort')

        cohort_user = CohortUser.objects.filter(user__id=user_id, cohort__id=cohort_id).first()

        if not is_post_method and not cohort_user:
            raise ValidationException('Cannot find CohortUser')

        if not id and cohort_user:
            id = cohort_user.id

        is_graduated = request_item.get('educational_status') == 'GRADUATED'
        is_late = (True if cohort_user and cohort_user.finantial_status == 'LATE' else
                   request_item.get('finantial_status') == 'LATE')
        if is_graduated and is_late:
            raise ValidationException('Cannot be marked as `GRADUATED` if its financial ' 'status is `LATE`')

        has_tasks = Task.objects.filter(user_id=user_id, task_status='PENDING',
                                        task_type='PROJECT').exclude(revision_status='IGNORED').count()
        if is_graduated and has_tasks:
            raise ValidationException(
                'User has tasks with status pending the educational status cannot be GRADUATED')

        data = {}

        for key in request_item:
            data[key] = request_item.get(key)

        data['cohort'] = cohort_id

        user = User.objects.filter(id=user_id).first()
        return {**data, 'id': id, 'cohort': cohort, 'user': user}


class CohortUserListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        books = [CohortUser(**item) for item in validated_data]
        items = CohortUser.objects.bulk_create(books)

        for key in range(0, len(items)):
            item = items[key]
            items[key].id = CohortUser.objects.filter(cohort__id=item.cohort_id,
                                                      user__id=item.user_id).values_list('id',
                                                                                         flat=True).first()

        return items

    def update(self, instance, validated_data):
        # Maps for id->instance and id->data item.
        model_mapping = {model.id: model for model in instance}
        data_mapping = {item['id']: item for item in validated_data}

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
    cohort = CohortSerializer(many=False, read_only=True)
    user = UserDJangoRestSerializer(many=False, read_only=True)

    class Meta:
        model = CohortUser
        fields = ['id', 'user', 'cohort', 'role']
        list_serializer_class = CohortUserListSerializer


class CohortTimeSlotSerializer(serializers.ModelSerializer):
    starting_at = serializers.IntegerField(write_only=True)
    ending_at = serializers.IntegerField(write_only=True)

    class Meta:
        model = CohortTimeSlot
        fields = ['id', 'cohort', 'starting_at', 'ending_at', 'recurrent', 'recurrency_type', 'timezone']


class SyllabusScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusSchedule
        exclude = ()


class SyllabusSchedulePUTSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    schedule_type = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    syllabus = serializers.IntegerField(required=False)

    class Meta:
        model = SyllabusSchedule
        exclude = ()


class SyllabusScheduleTimeSlotSerializer(serializers.ModelSerializer):
    starting_at = serializers.IntegerField(write_only=True)
    ending_at = serializers.IntegerField(write_only=True)

    class Meta:
        model = SyllabusScheduleTimeSlot
        fields = [
            'id',
            'schedule',
            'starting_at',
            'ending_at',
            'recurrent',
            'recurrency_type',
            'timezone',
        ]


class CohortUserPOSTSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    cohort = serpy.Field()
    user = serpy.Field()


class CohortUserPUTSerializer(CohortUserSerializerMixin):
    class Meta:
        model = CohortUser
        fields = ['id', 'role', 'educational_status', 'finantial_status']
        list_serializer_class = CohortUserListSerializer


class SyllabusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        fields = [
            'id', 'slug', 'name', 'academy_owner', 'duration_in_days', 'duration_in_hours', 'week_hours',
            'github_url', 'logo', 'private'
        ]
        exclude = ()


class SyllabusVersionSerializer(serializers.ModelSerializer):
    json = serializers.JSONField()

    class Meta:
        model = SyllabusVersion
        fields = ['json', 'version', 'syllabus', 'status', 'change_log_details']
        exclude = ()
        extra_kwargs = {
            'syllabus': {
                'read_only': True
            },
            'version': {
                'read_only': True
            },
        }

    def create(self, validated_data):
        syllabus = self.context['syllabus']

        previous_syllabus = SyllabusVersion.objects.filter(syllabus=syllabus).order_by('-version').first()

        version = 1
        if previous_syllabus is not None:
            version = previous_syllabus.version + 1

        return super(SyllabusVersionSerializer, self).create({
            **validated_data,
            'syllabus': syllabus,
            'version': version,
        })


class SyllabusVersionPutSerializer(serializers.ModelSerializer):
    json = serializers.JSONField()

    class Meta:
        model = SyllabusVersion
        fields = ['json', 'version', 'syllabus']
        exclude = ()
        extra_kwargs = {
            'syllabus': {
                'read_only': True
            },
            'version': {
                'read_only': True
            },
        }


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

        query = CohortUser.objects.filter(cohort__academy__id=obj.id, role='STUDENT')
        return {
            'total': query.count(),
            'active': query.filter(educational_status='ACTIVE').count(),
            'suspended': query.filter(educational_status='SUSPENDED').count(),
            'graduated': query.filter(educational_status='GRADUATED').count(),
            'dropped': query.filter(educational_status='DROPPED').count(),
        }

    teachers = serpy.MethodField()

    def get_teachers(self, obj):

        query = CohortUser.objects.filter(cohort__academy__id=obj.id,
                                          cohort__stage__in=['STARTED', 'FINAL_PROJECT'])
        active = {
            'main': query.filter(role='TEACHER').count(),
            'assistant': query.filter(role='ASSISTANT').count(),
            'reviewer': query.filter(role='REVIEWER').count(),
        }
        active['total'] = int(active['main']) + int(active['assistant']) + int(active['reviewer'])

        total = ProfileAcademy.objects.filter(role__slug__in=['teacher', 'assistant'])
        return {
            'total': total.count(),
            'active': active,
        }
