import hashlib
import serpy
import logging
import random
import os
import urllib.parse
import breathecode.notify.actions as notify_actions
from django.utils import timezone
from django.contrib.auth.models import User
from .models import CredentialsGithub, ProfileAcademy, Role, UserInvite, Profile, Token
from breathecode.utils import ValidationException
from breathecode.admissions.models import Academy, Cohort
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from django.db.models import Q

logger = logging.getLogger(__name__)

APP_URL = os.getenv('APP_URL', '')


class UserTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()


class AcademyTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()


class CohortTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()


class TokenSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    user = UserTinySerializer()
    key = serpy.Field()
    reset_password_url = serpy.MethodField()
    reset_github_url = serpy.MethodField()

    def get_reset_password_url(self, obj):
        return os.getenv('API_URL') + '/v1/auth/password/' + str(obj.key)

    def get_reset_github_url(self, obj):
        return os.getenv('API_URL') + '/v1/auth/github/' + str(obj.key)


class RoleSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.MethodField()
    slug = serpy.Field()
    name = serpy.Field()

    def get_id(self, obj):
        return obj.slug


class RoleBigSerializer(serpy.Serializer):
    """The serializer schema definition."""
    id = serpy.MethodField()
    slug = serpy.Field()
    name = serpy.Field()
    capabilities = serpy.MethodField()

    # this id is needed for zapier.com
    def get_id(self, obj):
        return obj.slug

    def get_capabilities(self, obj):
        return obj.capabilities.all().values_list('slug', flat=True)


class GithubSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    name = serpy.Field()
    username = serpy.Field()


class GetProfileSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()


class UserInviteSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    status = serpy.Field()
    email = serpy.Field()
    sent_at = serpy.Field()
    created_at = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    token = serpy.Field()
    academy = AcademyTinySerializer(required=False)
    cohort = CohortTinySerializer(required=False)
    role = RoleSmallSerializer(required=False)

    invite_url = serpy.MethodField()

    def get_invite_url(self, _invite):
        if _invite.token is None:
            return None
        return os.getenv('API_URL') + '/v1/auth/member/invite/' + str(_invite.token)


class AcademySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()
    timezone = serpy.Field()


class ProfileAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    academy = AcademySerializer()
    role = serpy.MethodField()
    created_at = serpy.Field()

    def get_role(self, obj):
        return obj.role.slug


class AcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class UserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()
    profile = serpy.MethodField()

    def get_github(self, obj):
        if not hasattr(obj, 'credentialsgithub'):
            return None

        return GithubSmallSerializer(obj.credentialsgithub).data

    def get_profile(self, obj):
        if not hasattr(obj, 'profile'):
            return None

        return GetProfileSmallSerializer(obj.profile).data


class UserSuperSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    profile = serpy.MethodField()

    def get_profile(self, obj):
        if not hasattr(obj, 'profile'):
            return None

        return GetProfileSmallSerializer(obj.profile).data


class GetProfileAcademySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    user = UserSmallSerializer(required=False)
    academy = AcademySmallSerializer()
    role = RoleSmallSerializer()
    created_at = serpy.Field()
    email = serpy.Field()
    address = serpy.Field()
    phone = serpy.Field()
    status = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    invite_url = serpy.MethodField()

    def get_invite_url(self, _invite):
        return os.getenv('API_URL') + '/v1/auth/academy/html/invite'


class GetProfileAcademySmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    user = UserSuperSmallSerializer(required=False)
    academy = AcademySmallSerializer()
    role = RoleSmallSerializer()
    created_at = serpy.Field()
    email = serpy.Field()
    address = serpy.Field()
    phone = serpy.Field()
    status = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()


# Create your models here.


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()
    roles = serpy.MethodField()

    def get_github(self, obj):
        github = CredentialsGithub.objects.filter(user=obj.id).first()
        if github is None:
            return None
        return GithubSmallSerializer(github).data

    def get_roles(self, obj):
        roles = ProfileAcademy.objects.filter(user=obj.id)
        return ProfileAcademySmallSerializer(roles, many=True).data


class GroupSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()


#
# CRUD SERIALIZERS BELOW
#


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAcademy
        fields = ('user', 'role', 'academy', 'first_name', 'last_name', 'address', 'phone', 'status')


class UserMeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        exclude = ()
        read_only_fields = ('user', )


class UserMeSerializer(serializers.ModelSerializer):
    profile = UserMeProfileSerializer(required=False)

    class Meta:
        model = User
        exclude = ('is_active', 'is_staff', 'password', 'username')

    # def create(self, validated_data):
    def update(self, instance, validated_data):

        profile_data = validated_data.pop('profile', None)

        if profile_data:
            serializer = None
            try:
                serializer = UserMeProfileSerializer(self.instance.profile,
                                                     data={
                                                         **profile_data, 'user': self.instance.id
                                                     })
            except Profile.DoesNotExist:
                serializer = UserMeProfileSerializer(data={**profile_data, 'user': self.instance.id})

            if serializer and serializer.is_valid():
                serializer.save()
            else:
                raise ValidationException('Error saving user profile')

        return super().update(self.instance, validated_data)


class MemberPOSTSerializer(serializers.ModelSerializer):
    invite = serializers.BooleanField(write_only=True, required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'role', 'user', 'first_name', 'last_name', 'address', 'phone', 'invite', 'status')

    def validate(self, data):
        if 'email' in data and data['email']:
            data['email'] = data['email'].lower()
            user = User.objects.filter(email=data['email']).first()

            if user:
                data['user'] = user.id

        if 'user' not in data:
            if 'invite' not in data or data['invite'] != True:
                raise ValidationException('User does not exists, do you want to invite it?',
                                          slug='user-not-found')

            elif 'email' not in data:
                raise ValidationException('Please specify user id or member email', slug='no-email-or-id')

            already = ProfileAcademy.objects.filter(email=data['email'],
                                                    academy=self.context['academy_id']).exists()

            if already:
                raise ValidationException(
                    'There is a member already in this academy with this email, or with invitation to this '
                    'email pending',
                    code=400,
                    slug='already-exists-with-this-email')

        elif 'user' in data:
            student_role = Role.objects.filter(slug='student').first()

            already = ProfileAcademy.objects.filter(
                user=data['user'], academy=self.context['academy_id']).exclude(role=student_role).first()
            if already:
                raise ValidationException(
                    f'This user is already a member of this academy as {str(already.role)}',
                    slug='already-exists')

        return data

    def create(self, validated_data):
        academy = Academy.objects.filter(id=self.context.get('academy_id')).first()
        if academy is None:
            raise ValidationException('Academy not found')

        role = validated_data['role']

        user = None
        email = None
        status = 'INVITED'

        # if the user already exists, we don't consider it and invite, we add the user immediately to the academy.
        if 'user' in validated_data:
            user = User.objects.filter(id=validated_data['user']).first()
            if user is None:
                raise ValidationException('User not found', code=400, slug='user-not-found')

            email = user.email
            status = 'ACTIVE'

            student_role = Role.objects.filter(slug='student').first()
            already_as_student = ProfileAcademy.objects.filter(user=user,
                                                               academy=academy.id,
                                                               role=student_role).first()
            # avoid double students on the same academy and cohort
            if already_as_student is not None:
                return super().update(
                    already_as_student, {
                        **validated_data,
                        'email': email,
                        'user': user,
                        'academy': academy,
                        'role': role,
                        'status': status,
                    })

        # if there is not user (first time) it will be considere an invite
        if 'user' not in validated_data:
            validated_data.pop('invite')  # the front end sends invite=true so we need to remove it
            email = validated_data['email'].lower()
            invite = UserInvite.objects.filter(email=email, author=self.context.get('request').user).first()

            # avoid double invite
            if invite is not None:
                raise ValidationException(
                    'You already invited this user, check for previous invites and resend',
                    code=400,
                    slug='already-invited')

            # prevent duplicate token (very low probability)
            while True:
                token = random.getrandbits(128)
                if not UserInvite.objects.filter(token=token).exists():
                    break

            invite = UserInvite(email=email,
                                first_name=validated_data['first_name'],
                                last_name=validated_data['last_name'],
                                academy=academy,
                                role=role,
                                author=self.context.get('request').user,
                                token=token)
            invite.save()

            logger.debug('Sending invite email to ' + email)

            params = {'callback': 'https://admin.breatheco.de'}
            querystr = urllib.parse.urlencode(params)
            url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
                str(invite.token) + '?' + querystr

            notify_actions.send_email_message(
                'welcome_academy', email, {
                    'email': email,
                    'subject': 'Welcome to 4Geeks',
                    'LINK': url,
                    'FIST_NAME': validated_data['first_name']
                })

        # add member to the academy (the cohort is inside validated_data
        return super().create({
            **validated_data,
            'email': email,
            'user': user,
            'academy': academy,
            'role': role,
            'status': status,
        })


# This method is almost repeated but now for students instead of academy memebers.
class StudentPOSTSerializer(serializers.ModelSerializer):
    invite = serializers.BooleanField(write_only=True, required=False)
    cohort = serializers.IntegerField(write_only=True, required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'user', 'first_name', 'last_name', 'address', 'phone', 'invite', 'cohort',
                  'status')

    def validate(self, data):
        if 'email' in data and data['email']:
            data['email'] = data['email'].lower()
            user = User.objects.filter(email=data['email']).first()

            if user:
                data['user'] = user.id

        if 'user' not in data:
            if 'invite' not in data or data['invite'] != True:
                raise ValidationException('User does not exists, do you want to invite it?',
                                          slug='user-not-found')
            elif 'email' not in data:
                raise ValidationException('Please specify user id or student email', slug='no-email-or-id')

            already = ProfileAcademy.objects.filter(email=data['email'],
                                                    academy=self.context['academy_id']).first()
            if already:
                raise ValidationException(
                    'There is a student already in this academy, or with invitation pending',
                    slug='already-exists-with-this-email')

        elif 'user' in data:
            already = ProfileAcademy.objects.filter(user=data['user'],
                                                    academy=self.context['academy_id']).first()
            if already:
                raise ValidationException('This user is already a member of this academy staff',
                                          code=400,
                                          slug='already-exists')

        return data

    def create(self, validated_data):

        academy = Academy.objects.filter(id=self.context.get('academy_id')).first()
        if academy is None:
            raise ValidationException('Academy not found')

        role = Role.objects.filter(slug='student').first()
        if role is None:
            raise ValidationException('Role student not found', slug='role-not-found')

        cohort = None
        if 'cohort' in validated_data:
            cohort = Cohort.objects.filter(id=validated_data.pop('cohort')).first()
            if cohort is None:
                raise ValidationException('Cohort not found', slug='cohort-not-found')

        user = None
        email = None
        status = 'INVITED'
        if 'user' in validated_data:
            user = User.objects.filter(id=validated_data['user']).first()
            if user is None:
                raise ValidationException('User not found', slug='user-not-found')

            email = user.email
            token, created = Token.get_or_create(user, token_type='temporal')
            querystr = urllib.parse.urlencode({'callback': APP_URL, 'token': token})
            url = os.getenv('API_URL') + '/v1/auth/academy/html/invite?' + querystr

            if 'invite' in validated_data:
                del validated_data['invite']

            profile_academy = ProfileAcademy.objects.create(
                **{
                    **validated_data,
                    'email': email,
                    'user': user,
                    'academy': academy,
                    'role': role,
                    'status': status,
                })
            profile_academy.save()

            notify_actions.send_email_message(
                'academy_invite', email, {
                    'subject': f'Invitation to study at {academy.name}',
                    'invites': [ProfileAcademySmallSerializer(profile_academy).data],
                    'user': UserSmallSerializer(user).data,
                    'LINK': url,
                })

            return profile_academy

        if 'user' not in validated_data:
            validated_data.pop('invite')
            email = validated_data['email']
            invite = UserInvite.objects.filter(email=validated_data['email'],
                                               author=self.context.get('request').user).first()
            if invite is not None:
                raise ValidationException('You already invited this user', code=400, slug='already-invited')

            # prevent duplicate token (very low probability)
            while True:
                token = random.getrandbits(128)
                if not UserInvite.objects.filter(token=token).exists():
                    break

            invite = UserInvite(email=validated_data['email'],
                                first_name=validated_data['first_name'],
                                last_name=validated_data['last_name'],
                                academy=academy,
                                cohort=cohort,
                                role=role,
                                author=self.context.get('request').user,
                                token=token)
            invite.save()

            logger.debug('Sending invite email to ' + email)

            querystr = urllib.parse.urlencode({'callback': APP_URL})
            url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
                str(invite.token) + '?' + querystr

            notify_actions.send_email_message(
                'welcome', email, {
                    'email': email,
                    'subject': 'Welcome to 4Geeks.com',
                    'LINK': url,
                    'FIST_NAME': validated_data['first_name']
                })

            return ProfileAcademy.objects.create(
                **{
                    **validated_data, 'email': email,
                    'user': user,
                    'academy': academy,
                    'role': role,
                    'status': status
                })


class MemberPUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAcademy
        fields = ('user', 'role', 'academy', 'first_name', 'last_name', 'phone', 'address')

    def validate(self, data):

        already = ProfileAcademy.objects.filter(user=data['user'], academy=data['academy']).first()
        if not already:
            raise ValidationError('User not found on this particular academy')

        return data

    def update(self, instance, validated_data):

        if instance.user.first_name is None or instance.user.first_name == '':
            instance.user.first_name = instance.first_name
        if instance.user.last_name is None or instance.user.last_name == '':
            instance.user.last_name = instance.last_name
        instance.user.save()

        return super().update(instance, validated_data)


class AuthSerializer(serializers.Serializer):
    email = serializers.EmailField(label='Email')
    password = serializers.CharField(label='Password',
                                     style={'input_type': 'password'},
                                     trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            email = email.lower()
            user = User.objects.filter(Q(email__iexact=email) | Q(username=email)).first()
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code=403)
            if user.check_password(password) != True:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code=403)
            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code=403)

        attrs['user'] = user
        return attrs


class UserInvitePUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInvite
        fields = ('status', 'id')

    def validate(self, data):

        if 'status' not in data:
            raise ValidationException('Missing status on invite')

        return data


class UserInviteWaitingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInvite

        fields = ('id', 'email', 'first_name', 'last_name', 'phone')

    def validate(self, data: dict[str, str]):
        if 'email' not in data:
            raise ValidationException('Email is required', slug='without-email')

        if UserInvite.objects.filter(email=data['email'], status='WAITING_LIST').exists():
            raise ValidationException('User already exists in the waiting list', slug='user-invite-exists')

        if User.objects.filter(email=data['email']).exists():
            raise ValidationException('User already exists, go ahead and log in instead.', slug='user-exists')

        now = str(timezone.now())

        data['status'] = 'WAITING_LIST'
        data['token'] = hashlib.sha1((now + data['email']).encode('UTF-8')).hexdigest()

        return data
