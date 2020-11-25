import serpy
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Academy, Cohort, Certificate, CohortUser

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
    avatar_url = serpy.Field()

class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    profile = ProfileSerializer(required=False)

class GETCohortUserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    user = UserSerializer()
    user = UserSerializer()
    role = serpy.Field()
    finantial_status = serpy.Field()
    educational_status = serpy.Field()
    created_at = serpy.Field()

class GetCertificateSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    logo = serpy.Field()

class GetAcademySerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    country = CountrySerializer(required=False)
    city = CitySerializer(required=False)
    logo_url = serpy.Field()

class GetCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    ending_date = serpy.Field()
    stage = serpy.Field()
    certificate = GetCertificateSerializer()
    academy = GetAcademySerializer()


"""
            ↓ EDIT SERLIZERS ↓
"""


class AcademySerializer(serializers.ModelSerializer):
    class Meta:
        model = Academy
        fields = ['id', 'slug', 'name', 'street_address']

class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = ('id', 'slug', 'name', 'kickoff_date')

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'slug', 'name']

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
        fields = ('slug', 'name', 'kickoff_date', 'ending_date', 'current_day', 'stage', 'language', 'certificate')

class UserDJangoRestSerializer(serializers.ModelSerializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    # id = serializers.IntegerField()
    # first_name = serializers.CharField()
    # last_name = serializers.CharField()
    # email = serializers.CharField()
    # profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']
        # fields = ['id', 'user']

class CohortUserSerializer(serializers.ModelSerializer):
# class CohortUserSerializer(serializers.Serializer):
    cohort = CohortSerializer(many=False, read_only=True)
    user = UserDJangoRestSerializer(many=False, read_only=True)
    # cohort = serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    # user = serializers.PrimaryKeyRelatedField(many=False, read_only=True)
    # cohort = serializers.IntegerField()
    # user = serializers.IntegerField()

    class Meta:
        model = CohortUser
        fields = ['id', 'user', 'cohort']
        # fields = ['id', 'user']

    # def create(self, validated_data):
    #     validated_data['cohort_id'] = validated_data.pop('cohort')
    #     validated_data['user_id'] = validated_data.pop('user')

    #     return CohortUser.objects.create(**validated_data)

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
