from breathecode.utils import ValidationException
from .models import MentorshipSession, MentorshipService, MentorProfile
from breathecode.admissions.models import Academy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import serpy, re
from django.utils import timezone


class GetAcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    icon_url = serpy.Field()


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    github_username = serpy.Field()


class GetSyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo = serpy.Field()


class GetUserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    profile = ProfileSerializer(required=False)


class GETServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()


class GETMentorSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    user = GetUserSmallSerializer()
    service = GETServiceSmallSerializer()
    status = serpy.Field()
    booking_url = serpy.Field()


class GETSessionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    mentor = GETMentorSmallSerializer()
    mentee = GetUserSmallSerializer(required=False)
    started_at = serpy.Field()
    ended_at = serpy.Field()
    mentor_joined_at = serpy.Field()
    mentor_left_at = serpy.Field()
    mentee_left_at = serpy.Field()
    summary = serpy.Field()


class GETServiceBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    academy = GetAcademySmallSerializer()
    logo_url = serpy.Field()
    description = serpy.Field()
    duration = serpy.Field()
    language = serpy.Field()
    allow_mentee_to_extend = serpy.Field()
    allow_mentors_to_extend = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class GETMentorBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    user = GetUserSmallSerializer()
    service = GETServiceBigSerializer()
    status = serpy.Field()
    price_per_hour = serpy.Field()
    booking_url = serpy.Field()
    timezone = serpy.Field()
    syllabus = serpy.MethodField()
    email = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_syllabus(self, obj):
        return map(lambda s: s.slug, obj.syllabus.all())


class GETSessionReportSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()
    starts_at = serpy.Field()
    ends_at = serpy.Field()
    mentor_joined_at = serpy.Field()
    mentor_left_at = serpy.Field()
    mentee_left_at = serpy.Field()
    mentor = GETMentorBigSerializer()
    mentee = GetUserSmallSerializer(required=False)


class GETSessionBigSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    mentor = GETMentorSmallSerializer()
    mentee = GetUserSmallSerializer(required=False)
    latitude = serpy.Field()
    longitude = serpy.Field()
    is_online = serpy.Field()
    online_meeting_url = serpy.Field()
    online_recording_url = serpy.Field()
    agenda = serpy.Field()
    summary = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()
    created_at = serpy.Field()


class ServicePOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipService
        exclude = ('created_at', 'updated_at', 'academy')

    def validate(self, data):

        academy = Academy.objects.filter(id=self.context['academy_id']).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy"]} not found',
                                      slug='academy-not-found')

        return {**data, 'academy': academy}


class ServicePUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipService
        exclude = ('created_at', 'updated_at', 'academy', 'slug')

    def validate(self, data):

        academy = Academy.objects.filter(id=self.context['academy_id']).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy"]} not found',
                                      slug='academy-not-found')

        if 'slug' in data:
            raise ValidationException('The service slug cannot be updated', slug='service-cannot-be-updated')

        return {**data, 'academy': academy}


class MentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        exclude = ('created_at', 'updated_at')


class MentorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        exclude = ('created_at', 'updated_at', 'user', 'token')

    def validate(self, data):

        if 'user' in data:
            raise ValidationException('Mentor user cannot be updated, please create a new mentor instead',
                                      slug='user-read-only')
        if 'token' in data:
            raise ValidationException('Mentor token cannot be updated', slug='token-read-only')

        if 'academy' in data:
            raise ValidationException('Mentor academy cannot be updated', slug='academy-read-only')

        return data


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        exclude = ('created_at', 'updated_at')

    # def validate(self, data):

    #     academy = Academy.objects.filter(id=self.context['academy']).first()
    #     if academy is None:
    #         raise ValidationException(f'Academy {self.context["academy"]} not found',
    #                                   slug='academy-not-found')

    #     return {**data, 'academy': academy}
