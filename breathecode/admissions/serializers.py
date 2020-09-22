import serpy
from rest_framework import serializers
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

class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    username = serpy.Field()
    email = serpy.Field()

class GetCertificateSerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    description = serpy.Field()
    logo = serpy.Field()

class GetAcademySerializer(serpy.Serializer):
    slug = serpy.Field()
    name = serpy.Field()
    country = CountrySerializer()
    city = CitySerializer()
    logo_url = serpy.Field()

class GetCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()
    kickoff_date = serpy.Field()
    certificate = GetCertificateSerializer()
    academy = GetAcademySerializer()

class AcademySerializer(serializers.ModelSerializer):
    class Meta:
        model = Academy
        fields = ['id', 'slug', 'name', 'street_address']

class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = ('slug', 'name', 'kickoff_date')

class CertificateSerializer(serializers.ModelSerializer):
        model = Certificate
        fields = ['id', 'slug', 'name']

class CohortUserSerializer(serializers.ModelSerializer):
    cohort = CohortSerializer(many=False)
    user = UserSerializer(many=False)

    class Meta:
        model = CohortUser
        fields = ['id', 'user', 'cohort']