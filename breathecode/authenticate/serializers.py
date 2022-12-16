import hashlib
from django.db import IntegrityError
import serpy
import logging
import random
import os
import urllib.parse
import breathecode.notify.actions as notify_actions
from django.utils import timezone
from django.contrib.auth.models import User
from .models import CredentialsGithub, ProfileAcademy, Role, UserInvite, Profile, Token, GitpodUser
from breathecode.utils import ValidationException
from breathecode.admissions.models import Academy, Cohort, Syllabus
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from django.db.models import Q
from django.contrib.auth.models import Permission

logger = logging.getLogger(__name__)

APP_URL = os.getenv('APP_URL', '')


class GetSmallCohortSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    slug = serpy.Field()
    name = serpy.Field()
    ending_date = serpy.Field()
    stage = serpy.Field()


class GetSmallAcademySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()
    slug = serpy.Field()


class UserTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    username = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    email = serpy.Field()


class UserBigSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()


class GitpodUserSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    github_username = serpy.Field()
    created_at = serpy.Field()
    delete_status = serpy.Field()
    assignee_id = serpy.Field()
    expires_at = serpy.Field()
    user = UserTinySerializer(required=False)
    academy = GetSmallAcademySerializer(required=False)
    target_cohort = GetSmallCohortSerializer(required=False)


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
    avatar_url = serpy.Field()


class GetProfileSerializer(serpy.Serializer):
    user = UserTinySerializer(many=False)
    avatar_url = serpy.Field()
    bio = serpy.Field()
    phone = serpy.Field()
    show_tutorial = serpy.Field()
    twitter_username = serpy.Field()
    github_username = serpy.Field()
    portfolio_url = serpy.Field()
    linkedin_url = serpy.Field()
    blog = serpy.Field()


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


class UserInviteSmallSerializer(serpy.Serializer):
    id = serpy.Field()
    academy = serpy.MethodField()
    cohort = serpy.MethodField()
    role = serpy.MethodField()
    created_at = serpy.Field()

    def get_role(self, obj):
        return obj.role.slug if obj.role else None

    def get_academy(self, obj):
        return AcademySerializer(obj.academy, many=False).data if obj.academy else None

    def get_cohort(self, obj):
        return GetSmallCohortSerializer(obj.cohort, many=False).data if obj.cohort else None


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


class GetProfileAcademyTinySerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    academy = AcademySmallSerializer()
    created_at = serpy.Field()
    email = serpy.Field()
    phone = serpy.Field()
    status = serpy.Field()


# this not include the content type
class GetPermissionSmallSerializer(serpy.Serializer):
    name = serpy.Field()
    codename = serpy.Field()


class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()
    roles = serpy.MethodField()
    profile = serpy.MethodField()
    permissions = serpy.MethodField()

    def get_permissions(self, obj):
        permissions = Permission.objects.none()

        for group in obj.groups.all():
            permissions |= group.permissions.all()

        return GetPermissionSmallSerializer(permissions.distinct().order_by('-id'), many=True).data

    def get_profile(self, obj):
        if not hasattr(obj, 'profile'):
            return None

        return GetProfileSmallSerializer(obj.profile).data

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
    cohort = serializers.ListField(child=serializers.IntegerField(write_only=True, required=False),
                                   write_only=True,
                                   required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'role', 'user', 'first_name', 'last_name', 'address', 'phone', 'invite', 'cohort',
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

        cohort = []
        if 'cohort' in validated_data:

            cohort_list = validated_data.pop('cohort')

            for cohort_id in cohort_list:
                cohort_search = Cohort.objects.filter(id=cohort_id).first()
                if cohort_search is None:
                    raise ValidationException('Cohort not found', slug='cohort-not-found')
                cohort.append(cohort_search)

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

            if (len(cohort) == 0):
                cohort = [None]

            for single_cohort in cohort:
                query = {
                    'cohort': single_cohort,
                    'email__iexact': email,
                    'author': self.context.get('request').user,
                }

                # if the cohort is not specified, process to find if the user was invite ignoring the cohort
                if not single_cohort:
                    del query['cohort']

                invite = UserInvite.objects.filter(**query).first()

                # avoid double invite
                if invite is not None:
                    raise ValidationException(
                        'You already invited this user, check for previous invites and resend',
                        code=400,
                        slug='already-invited')

            for single_cohort in cohort:
                # prevent duplicate token (very low probability)
                while True:
                    token = random.getrandbits(128)
                    if not UserInvite.objects.filter(token=token).exists():
                        break

                invite = UserInvite(email=email,
                                    first_name=validated_data['first_name'],
                                    last_name=validated_data['last_name'],
                                    academy=academy,
                                    cohort=single_cohort,
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


# This method is almost repeated but now for students instead of academy members.
class StudentPOSTListSerializer(serializers.ListSerializer):

    def create(self, validated_data):

        result = [self.child.create(attrs) for attrs in validated_data]

        try:
            self.child.Meta.model.objects.bulk_create(result)
        except IntegrityError as e:
            raise ValidationError(e)

        return result


# This method is almost repeated but now for students instead of academy memebers.
class StudentPOSTSerializer(serializers.ModelSerializer):
    invite = serializers.BooleanField(write_only=True, required=False)
    cohort = serializers.ListField(child=serializers.IntegerField(write_only=True, required=False),
                                   write_only=True,
                                   required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'user', 'first_name', 'last_name', 'address', 'phone', 'invite', 'cohort',
                  'status')
        list_serializer_class = StudentPOSTListSerializer

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

        cohort = []
        if 'cohort' in validated_data:

            cohort_list = validated_data.pop('cohort')

            for cohort_id in cohort_list:
                cohort_search = Cohort.objects.filter(id=cohort_id).first()
                if cohort_search is None:
                    raise ValidationException('Cohort not found', slug='cohort-not-found')
                cohort.append(cohort_search)

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
            validated_data.pop('invite')  # the front end sends invite=true so we need to remove it
            email = validated_data['email'].lower()

            if (len(cohort) == 0):
                cohort = [None]

            for single_cohort in cohort:
                query = {
                    'cohort': single_cohort,
                    'email__iexact': email,
                    'author': self.context.get('request').user,
                }

                # if the cohort is not specified, process to find if the user was invite ignoring the cohort
                if not single_cohort:
                    del query['cohort']

                invite = UserInvite.objects.filter(**query).first()
                if invite is not None:
                    raise ValidationException('You already invited this user',
                                              code=400,
                                              slug='already-invited')

            if (len(cohort) == 0):
                cohort = [None]

            for single_cohort in cohort:
                # prevent duplicate token (very low probability)
                while True:
                    token = random.getrandbits(128)
                    if not UserInvite.objects.filter(token=token).exists():
                        break

                invite = UserInvite(email=email,
                                    first_name=validated_data['first_name'],
                                    last_name=validated_data['last_name'],
                                    academy=academy,
                                    cohort=single_cohort,
                                    role=role,
                                    author=self.context.get('request').user,
                                    token=token)
                invite.save()

                logger.debug('Sending invite email to ' + email)

                querystr = urllib.parse.urlencode({'callback': APP_URL})
                url = os.getenv('API_URL') + '/v1/auth/member/invite/' + \
                    str(invite.token) + '?' + querystr

                notify_actions.send_email_message(
                    'welcome_academy', email, {
                        'email': email,
                        'subject': 'Welcome to 4Geeks.com',
                        'LINK': url,
                        'FIST_NAME': validated_data['first_name']
                    })

            return ProfileAcademy.objects.create(
                **{
                    **validated_data,
                    'email': email,
                    'user': user,
                    'academy': academy,
                    'role': role,
                    'status': status,
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
            instance.user.first_name = instance.first_name or ''
        if instance.user.last_name is None or instance.user.last_name == '':
            instance.user.last_name = instance.last_name or ''
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


class GetGitpodUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = GitpodUser
        exclude = ('updated_at', 'created_at', 'user', 'academy', 'assignee_id', 'github_username',
                   'position_in_gitpod_team', 'delete_status')


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        exclude = ()


class UserInviteWaitingListSerializer(serializers.ModelSerializer):
    access_token = serializers.SerializerMethodField()

    class Meta:
        model = UserInvite

        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'cohort', 'syllabus', 'access_token')

    def validate(self, data: dict[str, str]):
        if 'email' not in data:
            raise ValidationException('Email is required', slug='without-email')

        if not self.instance and UserInvite.objects.filter(email=data['email'],
                                                           status='WAITING_LIST').exists():
            raise ValidationException('User already exists in the waiting list', slug='user-invite-exists')

        user = User.objects.filter(email=data['email']).first()

        if not self.instance and user:
            raise ValidationException('User already exists, go ahead and log in instead.', slug='user-exists')

        self.user = user

        now = str(timezone.now())

        cohort = data.get('cohort')
        syllabus = data.get('syllabus')
        if cohort and cohort.academy and cohort.academy.available_as_saas == True:
            data['academy'] = cohort.academy
            data['cohort'] = cohort
            data['status'] = 'ACCEPTED'

        elif syllabus and Cohort.objects.filter(academy__available_as_saas=True,
                                                syllabus_version__syllabus=syllabus).exists():
            data['syllabus'] = syllabus
            data['status'] = 'ACCEPTED'

        else:
            data['status'] = 'WAITING_LIST'

        self.cohort = cohort
        self.syllabus = syllabus

        if not self.instance:
            data['token'] = hashlib.sha1((now + data['email']).encode('UTF-8')).hexdigest()

        print('data', data)

        return data

    def get_access_token(self, obj: UserInvite):
        without_cohort = not self.cohort or not self.cohort.academy or self.cohort.academy.available_as_saas != True
        without_syllabus = not self.syllabus or not Cohort.objects.filter(
            academy__available_as_saas=True, syllabus_version__syllabus=self.syllabus).exists()

        if without_cohort and without_syllabus:
            return None

        if not self.user:
            self.user = User(email=obj.email,
                             username=obj.email,
                             first_name=obj.first_name,
                             last_name=obj.last_name,
                             is_staff=False,
                             is_active=True)
            self.user.save()

            notify_actions.send_email_message(
                'pick_password', self.user.email, {
                    'SUBJECT': 'Set your password at 4Geeks',
                    'LINK': os.getenv('API_URL', '') + f'/v1/auth/password/{obj.token}'
                })

        token, _ = Token.get_or_create(user=self.user, token_type='login', hours_length=1 / 4)
        return token.key
