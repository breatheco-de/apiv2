from breathecode.admissions.actions import sync_cohort_timeslots
import logging
import serpy
from django.db.models import Q
from breathecode.assignments.models import Task
from breathecode.utils import ValidationException, localize_query
from rest_framework import serializers
from django.contrib.auth.models import User
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy
from .models import Academy, CertificateTimeSlot, Cohort, Certificate, CohortTimeSlot, CohortUser, Syllabus

logger = logging.getLogger(__name__)


class CountrySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    code = serpy.Field()
    name = serpy.Field()


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


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class ProfileAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    academy = AcademySerializer()
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


class GetCertificateSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    duration_in_days = serpy.Field()
    description = serpy.Field()
    logo = serpy.Field()


class GetSmallCertificateSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    duration_in_days = serpy.Field()


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


class SyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    certificate = GetSmallCertificateSerializer(required=False)


class SyllabusCertificateSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    certificate = GetTinnyCertificateSerializer(required=False)


class GetCohortSerializer(serpy.Serializer):
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
    stage = serpy.Field()
    syllabus = SyllabusSmallSerializer(required=False)
    academy = GetAcademySerializer()
    current_day = serpy.Field()


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
    syllabus = SyllabusSmallSerializer(required=False)
    academy = AcademySerializer()
    stage = serpy.Field()


class GETCohortUserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    user = UserSerializer()
    cohort = GetSmallCohortSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    created_at = serpy.Field()


class GETCohortTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.Field()
    cohort = serpy.MethodField()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    recurrent = serpy.Field()
    recurrency_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_cohort(self, obj):
        return obj.cohort.id


class GETCertificateTimeSlotSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.Field()
    academy = serpy.MethodField()
    certificate = serpy.MethodField()
    starting_at = serpy.Field()
    ending_at = serpy.Field()
    recurrent = serpy.Field()
    recurrency_type = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_academy(self, obj):
        return obj.academy.id

    def get_certificate(self, obj):
        return obj.certificate.id


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


class SyllabusGetSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    certificate = serpy.MethodField()
    updated_at = serpy.Field()
    json = serpy.Field()

    def get_certificate(self, obj):
        return obj.certificate.slug


"""
            ↓ EDIT SERLIZERS ↓
"""


class AcademySerializer(serializers.ModelSerializer):
    country = CountrySerializer(required=True)
    city = CitySerializer(required=True)

    class Meta:
        model = Academy
        fields = ['id', 'slug', 'name', 'street_address', 'country', 'city']

    def validate(self, data):

        if "slug" in data and data["slug"] != self.instance.slug:
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

    def validate(self, data):
        if 'syllabus' in data:
            strings = data['syllabus'].split('.v')

            if len(strings) != 2:
                raise ValidationException(
                    'Syllabus field marformed(`${certificate.slug}.v{syllabus.version}`)',
                    slug='syllabus-field-marformed'
                )

            [certificate_slug, syllabus_version] = strings
            syllabus = Syllabus.objects.filter(
                version=syllabus_version, certificate__slug=certificate_slug).first()

            if not syllabus:
                raise ValidationException(
                    'Syllabus doesn\'t exist',
                    slug='syllabus-doesnt-exist'
                )

            if not CertificateTimeSlot.objects.filter(certificate__id=syllabus.certificate.id).exists():
                raise ValidationException(
                    'We can\’t use a Syllabus if its certificate does not have any time slots',
                    slug='certificate-not-have-time-slots'
                )

            data['syllabus'] = syllabus

        if "slug" in data:
            cohort = Cohort.objects.filter(slug=data["slug"]).first()
            if cohort is not None and self.instance.slug != data["slug"]:
                raise ValidationException(
                    'Slug already exists for another cohort',
                    slug='slug-already-exists'
                )

        if self.instance:
            never_ends = (data['never_ends'] if 'never_ends' in
                data else self.instance.never_ends)

            ending_date = (data['ending_date'] if 'ending_date' in
                data else self.instance.ending_date)

        else:
            never_ends = 'never_ends' in data and data['never_ends']
            ending_date = 'ending_date' in data and data['ending_date']

        if never_ends and ending_date:
            raise ValidationException(
                'A cohort that never ends cannot have ending date',
                slug='cohort-with-ending-date-and-never-ends'
            )

        if not never_ends and not ending_date:
            raise ValidationException(
                'A cohort most have ending date or it should be marked as ever_ends',
                slug='cohort-without-ending-date-and-never-ends'
            )

        return data


class CohortSerializer(CohortSerializerMixin):
    academy = AcademySerializer(many=False, required=False, read_only=True)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date', 'current_day', 'academy', 'syllabus',
            'ending_date', 'stage', 'language', 'created_at', 'updated_at', 'never_ends')

    def create(self, validated_data):
        del self.context['request']
        cohort = Cohort.objects.create(**validated_data, **self.context)
        sync_cohort_timeslots(cohort.id)
        return cohort


class CohortPUTSerializer(CohortSerializerMixin):
    # id = serializers.IntegerField(required=True)
    slug = serializers.SlugField(required=False)
    name = serializers.CharField(required=False)
    private = serializers.BooleanField(required=False)
    kickoff_date = serializers.DateTimeField(required=False)
    ending_date = serializers.DateTimeField(required=False, allow_null=True)
    current_day = serializers.IntegerField(required=False)
    stage = serializers.CharField(required=False)
    language = serializers.CharField(required=False)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date', 'ending_date', 'current_day', 'stage', 'language',
            'syllabus', 'never_ends', 'private')


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
        return CohortUser.objects.filter(user_id=user_id, role='STUDENT', cohort__syllabus__certificate=cohort.syllabus.certificate).filter(Q(educational_status='ACTIVE') | Q(educational_status__isnull=True)).count()

    def validate_just_one(self):
        pass

    def validate(self, data):
        self.index = self.index + 1

        request = self.context['request']
        is_many = isinstance(request.data, list)
        cohort_id = self.context['cohort_id']
        user_id = self.context['user_id']
        disable_cohort_user_just_once = True
        disable_certificate_validations = True
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
            ids = CohortUser.objects.filter(id=id).values_list(
                'user_id', 'cohort_id').first()

            if not ids:
                raise ValidationException("Invalid id", code=400)
            user_id = ids[0]
            cohort_id = ids[1]

        if user_id is None:
            user_id = request_item.get('user')

        if not is_many and (cohort_id is None or user_id is None):
            raise ValidationException("Missing cohort_id or user_id", code=400)

        if User.objects.filter(id=user_id).count() == 0:
            raise ValidationException("invalid user_id", code=400)

        cohort = Cohort.objects.filter(id=cohort_id)
        if not cohort:
            raise ValidationException("invalid cohort_id", code=400)

        # only from this academy
        cohort = localize_query(cohort, request).first()

        if cohort is None:
            logger.debug(f"Cohort not be found in related academies")
            raise ValidationException('Specified cohort not be found')

        if not disable_cohort_user_just_once and CohortUser.objects.filter(user_id=user_id,
                                                                           cohort_id=cohort_id).count():
            raise ValidationException(
                'That user already exists in this cohort')

        if ('role' in request_item and request_item['role'] != 'STUDENT' and
                not ProfileAcademy.objects.filter(
                    user_id=user_id,
                    academy__id=cohort.academy.id).exclude(role__slug='student')
                        .exists()):
            raise ValidationException(
                'The user must be staff member to this academy before it can be a teacher')

        if (is_post_method and cohort.syllabus and
                self.count_certificates_by_cohort(cohort, user_id) > 0):
            raise ValidationException(
                'This student is already in another cohort for the same certificate, please mark him/her hi educational status on this prior cohort different than ACTIVE before cotinuing')

        role = request_item.get('role')
        if role == 'TEACHER' and CohortUser.objects.filter(role=role, cohort_id=cohort_id).exclude(user__id__in=[user_id]).count():
            raise ValidationException(
                'There can only be one main instructor in a cohort')

        cohort_user = CohortUser.objects.filter(
            user__id=user_id, cohort__id=cohort_id).first()

        if not is_post_method and not cohort_user:
            raise ValidationException('Cannot find CohortUser')

        if not id and cohort_user:
            id = cohort_user.id

        is_graduated = request_item.get('educational_status') == 'GRADUATED'
        is_late = (True if cohort_user and cohort_user.finantial_status == 'LATE' else request_item
                   .get('finantial_status') == 'LATE')
        if is_graduated and is_late:
            raise ValidationException(('Cannot be marked as `GRADUATED` if its financial '
                                       'status is `LATE`'))

        has_tasks = Task.objects.filter(user_id=user_id, task_status='PENDING',
                                        task_type='PROJECT').count()
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
            items[key].id = CohortUser.objects.filter(
                cohort__id=item.cohort_id, user__id=item.user_id).values_list('id', flat=True).first()

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
    class Meta:
        model = CohortTimeSlot
        fields = ['id', 'cohort', 'starting_at', 'ending_at', 'recurrent',
            'recurrency_type']


class CertificateTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTimeSlot
        fields = ['id', 'academy', 'certificate', 'starting_at', 'ending_at', 'recurrent',
            'recurrency_type']


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


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        exclude = ()


class SyllabusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        exclude = ()
        extra_kwargs = {
            'certificate': {'read_only': True},
            'version': {'read_only': True},
        }

    def create(self, validated_data):

        previous_syllabus = Syllabus.objects.filter(
            academy_owner=self.context['academy'], certificate=self.context['certificate']).order_by('-version').first()
        version = 1
        if previous_syllabus is not None:
            version = previous_syllabus.version + 1
        return super(SyllabusSerializer, self).create({
            **validated_data,
            "certificate": self.context['certificate'],
            "academy_owner": self.context['academy'],
            "version": version
        })


class SyllabusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        exclude = ()
        extra_kwargs = {
            'course': {'read_only': True},
            'version': {'read_only': True},
        }
