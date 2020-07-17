import serpy
from rest_framework import serializers
from .models import Academy, Cohort, Certificate, CohortUser

class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    username = serpy.Field()
    email = serpy.Field()

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