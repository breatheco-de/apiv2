from breathecode.utils import ValidationException
from .models import MentorshipSession, MentorshipService, MentorProfile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy, re
from django.utils import timezone


class GetAcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GetUserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class GETServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()


class GETMentorSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    user = GetUserSmallSerializer()
    service = GETServiceSmallSerializer()
    status = serpy.Field()


class GETSessionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    mentor = GETMentorSmallSerializer()
    mentee = GetUserSmallSerializer()


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipService
        exclude = ('created_at', 'updated_at')


class MentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        exclude = ('created_at', 'updated_at')


class MentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        exclude = ('created_at', 'updated_at')
