import serpy
from breathecode.utils import ValidationException
from .models import MentorshipSession, MentorshipService, MentorProfile, MentorshipBill
import breathecode.mentorship.actions as actions
from .actions import generate_mentor_bill
from breathecode.admissions.models import Academy
from rest_framework import serializers
from breathecode.utils.datetime_interger import duration_to_str
from breathecode.authenticate.models import ProfileAcademy
from breathecode.utils.i18n import translation


class GetAcademySmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo_url = serpy.Field()
    icon_url = serpy.Field()


class TinyBillSerializer(serpy.Serializer):
    status = serpy.Field()
    id = serpy.Field()


class AnswerSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    title = serpy.Field()
    lowest = serpy.Field()
    highest = serpy.Field()
    comment = serpy.Field()
    score = serpy.Field()
    status = serpy.Field()


class ProfileSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    github_username = serpy.Field()


class ProfilePublicSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class GetSyllabusSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    logo = serpy.Field()


class GetUserPublicTinySerializer(serpy.Serializer):
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = ProfilePublicSerializer(required=False)


class GetUserSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()
    profile = ProfileSerializer(required=False)


class SlackChannelTinySerializer(serpy.Serializer):
    slack_id = serpy.Field()
    name = serpy.Field()


class SupportChannelTinySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()

    created_at = serpy.Field()
    updated_at = serpy.Field()


class GETAgentSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    email = serpy.Field()
    status = serpy.Field()
    channel = SupportChannelTinySerializer()
    user = GetUserSmallSerializer()

    created_at = serpy.Field()
    updated_at = serpy.Field()


class GETSupportChannelSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    slack_channel = SlackChannelTinySerializer(required=False)
    academy = GetAcademySmallSerializer()
    syllabis = serpy.MethodField()

    def get_syllabis(self, obj):
        return GetSyllabusSmallSerializer(obj.syllabis.all(), many=True).data


class GETServiceTinySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    duration = serpy.Field()


class GETServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    duration = serpy.Field()
    max_duration = serpy.Field()
    missed_meeting_duration = serpy.Field()
    language = serpy.Field()
    allow_mentee_to_extend = serpy.Field()
    allow_mentors_to_extend = serpy.Field()


class GETMentorPublicTinySerializer(serpy.Serializer):
    user = GetUserPublicTinySerializer()


class GETMentorTinySerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    user = GetUserSmallSerializer()
    services = serpy.MethodField()
    status = serpy.Field()
    booking_url = serpy.Field()

    def get_services(self, obj):
        return GETServiceSmallSerializer(obj.services.all(), many=True).data


class GETSessionSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    mentor = GETMentorTinySerializer()
    service = GETServiceTinySerializer(required=False)
    mentee = GetUserSmallSerializer(required=False)
    started_at = serpy.Field()
    ended_at = serpy.Field()
    mentor_joined_at = serpy.Field()
    mentor_left_at = serpy.Field()
    mentee_left_at = serpy.Field()
    allow_billing = serpy.Field()
    accounted_duration = serpy.Field()
    summary = serpy.Field()

    bill = TinyBillSerializer(required=False)


class GETServiceSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    academy = GetAcademySmallSerializer()
    logo_url = serpy.Field()
    duration = serpy.Field()
    language = serpy.Field()
    allow_mentee_to_extend = serpy.Field()
    allow_mentors_to_extend = serpy.Field()
    max_duration = serpy.Field()
    missed_meeting_duration = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()


class GETServiceBigSerializer(GETServiceSmallSerializer):
    description = serpy.Field()


class GETMentorSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    user = GetUserSmallSerializer()
    services = serpy.MethodField()
    status = serpy.Field()
    one_line_bio = serpy.Field()
    rating = serpy.Field()
    price_per_hour = serpy.Field()
    booking_url = serpy.Field()
    online_meeting_url = serpy.Field()
    timezone = serpy.Field()
    email = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_services(self, obj):
        return GETServiceSmallSerializer(obj.services.all(), many=True).data


class GETBillSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    status = serpy.Field()
    total_duration_in_minutes = serpy.Field()
    total_duration_in_hours = serpy.Field()
    total_price = serpy.Field()
    started_at = serpy.Field()
    ended_at = serpy.Field()
    overtime_minutes = serpy.Field()
    paid_at = serpy.Field()
    created_at = serpy.Field()

    mentor = GETMentorTinySerializer()
    reviewer = GetUserSmallSerializer(required=False)


class BigBillSerializer(GETBillSmallSerializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    overtime_hours = serpy.MethodField()
    sessions = serpy.MethodField()
    unfinished_sessions = serpy.MethodField()
    public_url = serpy.MethodField()
    academy = GetAcademySmallSerializer(required=False)
    mentor = GETMentorSmallSerializer()

    def get_overtime_hours(self, obj):
        return round(obj.overtime_minutes / 60, 2)

    def get_sessions(self, obj):
        _sessions = obj.mentorshipsession_set.order_by('created_at').all()
        return BillSessionSerializer(_sessions, many=True).data

    def get_unfinished_sessions(self, obj):
        _sessions = MentorshipSession.objects.filter(
            mentor=obj.mentor, bill__isnull=True, allow_billing=True,
            bill__academy=obj.academy).exclude(status__in=['COMPLETED', 'FAILED'])
        return BillSessionSerializer(_sessions, many=True).data

    def get_public_url(self, obj):
        return '/v1/mentorship/academy/bill/1/html'


class GETMentorBigSerializer(serpy.Serializer):
    id = serpy.Field()
    slug = serpy.Field()
    user = GetUserSmallSerializer()
    services = serpy.MethodField()
    status = serpy.Field()
    price_per_hour = serpy.Field()
    booking_url = serpy.Field()
    online_meeting_url = serpy.Field()
    timezone = serpy.Field()
    syllabus = serpy.MethodField()
    one_line_bio = serpy.Field()
    rating = serpy.Field()
    email = serpy.Field()
    created_at = serpy.Field()
    updated_at = serpy.Field()

    def get_syllabus(self, obj):
        return GetSyllabusSmallSerializer(obj.syllabus.all(), many=True).data

    def get_services(self, obj):
        return GETServiceBigSerializer(obj.services.all(), many=True).data


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
    allow_billing = serpy.Field()
    accounted_duration = serpy.Field()
    suggested_accounted_duration = serpy.Field()
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
    allow_billing = serpy.Field()
    online_meeting_url = serpy.Field()
    online_recording_url = serpy.Field()
    agenda = serpy.Field()
    summary = serpy.Field()
    started_at = serpy.Field()
    accounted_duration = serpy.Field()
    suggested_accounted_duration = serpy.Field()
    ended_at = serpy.Field()
    created_at = serpy.Field()


class BillSessionSerializer(serpy.Serializer):
    id = serpy.Field()
    status = serpy.Field()
    status_message = serpy.Field()
    mentor = GETMentorSmallSerializer()
    mentee = GetUserSmallSerializer(required=False)
    started_at = serpy.Field()
    ended_at = serpy.Field()
    mentor_joined_at = serpy.Field()
    mentor_left_at = serpy.Field()
    mentee_left_at = serpy.Field()
    summary = serpy.Field()
    accounted_duration = serpy.Field()
    suggested_accounted_duration = serpy.Field()

    tooltip = serpy.MethodField()
    duration_string = serpy.MethodField()
    billed_str = serpy.MethodField()
    extra_time = serpy.MethodField()
    mentor_late = serpy.MethodField()
    mentee_joined = serpy.MethodField()
    rating = serpy.MethodField()

    def get_tooltip(self, obj):
        service = obj.service

        if service is None:
            return 'Please ser service for this mentorship'

        message = f'This mentorship should last no longer than {int(service.duration.seconds/60)} min. <br />'
        if obj.started_at is None:
            message += 'The mentee never joined the session. <br />'
        else:
            message += f'Started on {obj.started_at.strftime("%m/%d/%Y at %H:%M:%S")}. <br />'
            if obj.mentor_joined_at is None:
                message += f'The mentor never joined'
            elif obj.mentor_joined_at > obj.started_at:
                message += f'The mentor joined {duration_to_str(obj.mentor_joined_at - obj.started_at)} before. <br />'
            elif obj.started_at > obj.mentor_joined_at:
                message += f'The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />'

            if obj.ended_at is not None:
                message += f'The mentorship lasted {duration_to_str(obj.ended_at - obj.started_at)}. <br />'

                if (obj.ended_at - obj.started_at) > service.duration:
                    extra_time = (obj.ended_at - obj.started_at) - service.duration

                    message += f'With extra time of {duration_to_str(extra_time)}. <br />'
                else:
                    message += f'No extra time detected <br />'
            else:
                message += f'The mentorship has not ended yet. <br />'
                if obj.ends_at is not None:
                    message += f'But it was supposed to end after {duration_to_str(obj.ends_at - obj.started_at)} <br />'

        return message

    def get_duration_string(self, obj):

        if obj.started_at is None:
            return 'Never started'

        end_date = obj.ended_at
        if end_date is None:
            return 'Never ended'

        if obj.started_at > end_date:
            return 'Ended before it started'

        if (end_date - obj.started_at).days > 1:
            return f'Many days'

        return duration_to_str(obj.ended_at - obj.started_at)

    def get_billed_str(self, obj):
        return duration_to_str(obj.accounted_duration)

    def get_accounted_duration_string(self, obj):
        return duration_to_str(obj.accounted_duration)

    def get_extra_time(self, obj):

        if obj.started_at is None or obj.ended_at is None:
            return None

        if (obj.ended_at - obj.started_at).days > 1:
            return f'Many days of extra time, probably it was never closed'

        if obj.service is None:
            return 'Please setup service for this session'

        if (obj.ended_at - obj.started_at) > obj.service.duration:
            extra_time = (obj.ended_at - obj.started_at) - obj.service.duration
            return f'Extra time of {duration_to_str(extra_time)}, the expected duration was {duration_to_str(obj.service.duration)}'
        else:
            return None

    def get_mentor_late(self, obj):

        if obj.started_at is None or obj.mentor_joined_at is None:
            return None

        if obj.started_at > obj.mentor_joined_at and (obj.started_at - obj.mentor_joined_at).seconds > (60 *
                                                                                                        4):
            return f'The mentor joined {duration_to_str(obj.started_at - obj.mentor_joined_at)} after. <br />'
        else:
            return None

    def get_mentee_joined(self, obj):

        if obj.started_at is None:
            return 'Session did not start because mentee never joined'
        else:
            return True

    def get_rating(self, obj):

        answer = obj.answer_set.first()
        if answer is None:
            return None
        else:
            return AnswerSmallSerializer(answer).data


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
    name = serializers.CharField(required=False)

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
    academy = serializers.PrimaryKeyRelatedField(queryset=Academy.objects.all(), required=True)

    class Meta:
        model = MentorProfile
        exclude = ('created_at', 'updated_at')

    def validate(self, data):
        lang = data.get('lang', 'en')
        academy_id = data['academy'].id if 'academy' in data else 0
        user = data['user']
        profile_academy = ProfileAcademy.objects.filter(user__id=data['user'].id,
                                                        academy__id=data['academy'].id).first()

        if 'name' not in data:
            data['name'] = ''

        if not data['name'] and profile_academy:
            data['name'] = profile_academy.first_name + ' ' + profile_academy.last_name

        if not data['name']:
            data['name'] = user.first_name + ' ' + user.last_name
        data['name'] = data['name'].strip()

        if 'None' in data['name']:
            data['name'] = ''

        if not data['name']:
            raise ValidationException(translation(lang,
                                                  en='Unable to find name on this user',
                                                  es='imposible encontrar el nombre en este usuario',
                                                  slug='name-not-found'),
                                      code=400)

        if 'email' not in data:
            data['email'] = ''

        if not data['email'] and profile_academy:

            data['email'] = profile_academy.email

        if not data['email']:

            data['email'] = data['user'].email

        if not data['email']:
            raise ValidationException(translation(lang,
                                                  en='Unable to find email on this user',
                                                  es='Imposible encontrar el email en este usuario',
                                                  slug='email-not-found'),
                                      code=400)

        return data


class MentorUpdateSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False)
    price_per_hour = serializers.FloatField(required=False)

    services = serializers.PrimaryKeyRelatedField(queryset=MentorshipService.objects.all(),
                                                  required=False,
                                                  many=True)

    class Meta:
        model = MentorProfile
        exclude = ('created_at', 'updated_at', 'user', 'token')

    def validate(self, data):
        lang = data.get('lang', 'en')
        if 'status' in data and data['status'] in ['ACTIVE', 'UNLISTED'
                                                   ] and self.instance.status != data['status']:
            try:
                actions.mentor_is_ready(self.instance)
            except Exception as e:
                raise ValidationException(str(e))

        user = data['user'] if 'user' in data else self.instance.user
        academy = data['academy'] if 'academy' in data else self.instance.academy
        profile_academy = ProfileAcademy.objects.filter(user__id=user.id, academy=academy).first()

        if 'name' not in data:
            data['name'] = ''

        if not data['name'] and profile_academy:

            data['name'] = profile_academy.first_name + ' ' + profile_academy.last_name

        if 'None' in data['name']:
            data['name'] = ''

        data['name'] = data['name'].strip()
        if not data['name']:
            raise ValidationException(translation(lang,
                                                  en='Unable to find name on this user',
                                                  es='Imposible encotrar el nombre en este usuario',
                                                  slug='name-not-found'),
                                      code=400)

        if 'email' not in data:
            data['email'] = self.instance.email

        if not data['email'] and profile_academy:

            data['email'] = profile_academy.email

        if not data['email']:
            raise ValidationException(translation(lang,
                                                  en='Unable to find email on this user',
                                                  es='Imposible encontrar el email en este usuario',
                                                  slug='email-imposible-to-find'),
                                      code=400)

        return data


class SessionListSerializer(serializers.ListSerializer):

    def update(self, instances, validated_data):

        instance_hash = {index: instance for index, instance in enumerate(instances)}

        result = [
            self.child.update(instance_hash[index], attrs) for index, attrs in enumerate(validated_data)
        ]

        return result


class SessionPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = MentorshipSession
        list_serializer_class = SessionListSerializer
        exclude = (
            'created_at',
            'updated_at',
            'suggested_accounted_duration',
            'status_message',
        )

    def validate(self, data):
        #is_online
        if 'is_online' in data and data['is_online'] == True:
            online_read_only = [
                'mentor_joined_at',
                'mentor_left_at',
                'mentee_left_at',
                'started_at',
                'ended_at',
            ]
            for field in online_read_only:
                if field in data:
                    raise ValidationException(
                        f'The field {field} is automatically set by the system during online mentorships',
                        slug='read-only-field-online')

        return super().validate(data)

    def update(self, instance, validated_data):
        result = super().update(instance, validated_data)

        bill = MentorshipBill.objects.filter(id=instance.bill_id).first()
        if bill is None:
            return result

        mentor = MentorProfile.objects.filter(id=instance.mentor_id).first()

        sessions = bill.mentorshipsession_set.all()

        success_status = ['APPROVED', 'PAID', 'IGNORED']
        is_dirty = [x for x in sessions if x.bill.status not in success_status and not x.service]

        # this prevent errors 500
        if not is_dirty:
            generate_mentor_bill(mentor, bill, bill.mentorshipsession_set.all())

        else:
            bill.status = 'RECALCULATE'
            bill.save()

        return result


class SessionSerializer(SessionPUTSerializer):
    service = serializers.PrimaryKeyRelatedField(queryset=MentorshipService.objects.all(), required=True)


class MentorshipBillPUTListSerializer(serializers.ListSerializer):

    def update(self, instances, validated_data):

        instance_hash = {index: instance for index, instance in enumerate(instances)}

        result = [
            self.child.update(instance_hash[index], attrs) for index, attrs in enumerate(validated_data)
        ]

        return result


class MentorshipBillPUTSerializer(serializers.ModelSerializer):

    class Meta:
        model = MentorshipBill
        exclude = ('created_at', 'updated_at', 'academy', 'mentor', 'reviewer', 'total_duration_in_minutes',
                   'total_duration_in_hours', 'total_price', 'overtime_minutes')
        list_serializer_class = MentorshipBillPUTListSerializer

    def validate(self, data):

        academy = Academy.objects.filter(id=self.context['academy_id']).first()
        if academy is None:
            raise ValidationException(f'Academy {self.context["academy_id"]} not found',
                                      slug='academy-not-found')

        return {**data, 'academy': academy}
