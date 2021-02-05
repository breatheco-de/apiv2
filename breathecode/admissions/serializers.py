import serpy
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from breathecode.authenticate.models import CredentialsGithub, ProfileAcademy
from .models import Academy, Cohort, Certificate, CohortUser, Syllabus

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

    def get_role(self,obj):
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
    description = serpy.Field()
    logo = serpy.Field()

class GetSmallCertificateSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()

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

class SyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    version = serpy.Field()
    certificate = GetSmallCertificateSerializer(required=False)

class GetCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    language = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    stage = serpy.Field()
    syllabus = SyllabusSmallSerializer()
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
    syllabus = SyllabusSmallSerializer()
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


class SyllabusPOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        fields = ['id', 'slug']


class CohortSerializer(serializers.ModelSerializer):
    academy = AcademySerializer(many=False, required=False, read_only=True)
    syllabus = SyllabusPOSTSerializer(many=False, required=False, read_only=True)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date', 'current_day', 'academy', 'syllabus',
            'ending_date', 'stage', 'language', 'created_at', 'updated_at')

    def create(self, validated_data):
        return Cohort.objects.create(**self.context)

    def validate(self, data):

        # cohort slug cannot be used by another cohort
        cohort = Cohort.objects.filter(slug=data['slug']).first()
        if cohort is not None:
            raise ValidationError('This cohort slug is already taken')

        return data

class CohortPUTSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False)
    name = serializers.CharField(required=False)
    kickoff_date = serializers.DateTimeField(required=False)
    ending_date = serializers.DateTimeField(required=False)
    current_day = serializers.IntegerField(required=False)
    stage = serializers.CharField(required=False)
    language = serializers.CharField(required=False)

    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date', 'ending_date', 'current_day', 'stage', 'language',
            'syllabus')

    def validate(self, data):


        if "slug" in data:
            cohort = Cohort.objects.filter(slug=data["slug"]).first()
            if cohort is not None and self.instance.slug != data["slug"]:
                raise ValidationError('Slug already exists for another cohort')
        
        return data

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

class CohortUserSerializer(serializers.ModelSerializer):
    cohort = CohortSerializer(many=False, read_only=True)
    user = UserDJangoRestSerializer(many=False, read_only=True)

    class Meta:
        model = CohortUser
        fields = ['id', 'user', 'cohort', 'role']

    def create(self, validated_data):
        # relationships, thank you amazing and incredible serializer!
        cohort = self.context.get('cohort')
        user = self.context.get('user')

        return CohortUser.objects.create(**validated_data, cohort_id=cohort, user_id=user)

class CohortUserPOSTSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    cohort = serpy.Field()
    user = serpy.Field()

# class CohortUserSerializer(serializers.ModelSerializer):
#     cohort = CohortSerializer(many=False)
#     user = UserSerializer(many=False)

#     class Meta:
#         model = CohortUser
#         fields = ['id', 'user', 'cohort']

class CohortUserPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = CohortUser
        fields = ['id', 'role', 'educational_status', 'finantial_status']

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        exclude = ()

class SyllabusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        exclude = ()
        extra_kwargs = {
            'course': {'read_only': True},
            'version': {'read_only': True},
        }

    def create(self, validated_data):
        previous_syllabus = Syllabus.objects.filter(course__id=self.context['course'].id, academy_owner=self.context['academy']).order_by('-version').first()
        version = 1
        if previous_syllabus is not None:
            version = previous_syllabus.version + 1
        return super(SyllabusSerializer, self).create({ 
            **validated_data,
            "course": self.context['course'],
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