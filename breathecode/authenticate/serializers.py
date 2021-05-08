import serpy, logging, random, os
import urllib.parse
from django.contrib.auth.models import User, Group
from .models import CredentialsGithub, ProfileAcademy, Role, UserInvite, Profile
from breathecode.utils import ValidationException
from breathecode.admissions.models import Academy, Cohort
from breathecode.notify.actions import send_email_message
from django.db import models
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.db.models import Q

logger = logging.getLogger(__name__)


class RoleSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    slug = serpy.Field()
    name = serpy.Field()


class GithubSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    name = serpy.Field()
    username = serpy.Field()


class UserInviteSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    status = serpy.Field()
    email = serpy.Field()
    sent_at = serpy.Field()
    created_at = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    token = serpy.Field()

    invite_url = serpy.MethodField()

    def get_invite_url(self, _invite):
        if _invite.token is None:
            return None
        return os.getenv('API_URL') + "/v1/auth/member/invite/" + str(_invite.token)


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

    def get_github(self, obj):
        github = CredentialsGithub.objects.filter(user=obj.id).first()
        if github is None:
            return None
        return GithubSmallSerializer(github).data


class GETProfileAcademy(serpy.Serializer):
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
        fields = ('user', 'role', 'academy', 'first_name',
                  'last_name', 'address', 'phone', 'status')


class UserMeProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        exclude = ()
        read_only_fields = ('user',)


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
                serializer = UserMeProfileSerializer(self.instance.profile, data={
                                                     **profile_data, "user": self.instance.id})
            except Profile.DoesNotExist:
                serializer = UserMeProfileSerializer(
                    data={**profile_data, "user": self.instance.id})

            if serializer and serializer.is_valid():
                serializer.save()
            else:
                raise ValidationException("Error saving user profile")

        return super().update(self.instance, validated_data)


class MemberPOSTSerializer(serializers.ModelSerializer):
    invite = serializers.BooleanField(write_only=True, required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'role', 'user', 'first_name', 'last_name',
                  'address', 'phone', 'invite', 'status')

    def validate(self, data):
        if "user" not in data:
            if "invite" not in data or data["invite"] != True:
                raise ValidationException(
                    "User does not exists, do you want to invite it?")
            elif "email" not in data:
                raise ValidationException(
                    "Please specify user id or member email")

            already = ProfileAcademy.objects.filter(
                email=data['email'], academy=self.context['academy_id']).first()
            if already:
                raise ValidationException(
                    'There is a member already in this academy with this email, or with invitation to this email pending')

        elif "user" in data:
            already = ProfileAcademy.objects.filter(
                user=data['user'], academy=self.context['academy_id']).first()
            if already:
                raise ValidationException(
                    'This user is already a member of this academy staff')

        if "role" not in data:
            raise ValidationException("Missing role")

        return data

    def create(self, validated_data):

        academy = Academy.objects.filter(
            id=self.context.get('academy_id')).first()
        if academy is None:
            raise ValidationException("Academy not found")

        role = validated_data['role']

        user = None
        email = None
        status = "INVITED"
        if "user" in validated_data:
            user = User.objects.filter(id=validated_data["user"]).first()
            if user is None:
                raise ValidationException("User not found")
            email = user.email
            status = "ACTIVE"

        if "user" not in validated_data:
            validated_data.pop('invite')
            email = validated_data["email"].lower()
            invite = UserInvite.objects.filter(
                email=email, author=self.context.get('request').user).first()
            if invite is not None:
                raise ValidationException(
                    "You already invited this user, check for previous invites and resend")

            invite = UserInvite(
                email=email,
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                academy=academy,
                role=role,
                author=self.context.get('request').user,
                token=random.getrandbits(128)
            )
            invite.save()

            logger.debug("Sending invite email to "+email)

            params = {"callback": "https://admin.breatheco.de"}
            querystr = urllib.parse.urlencode(params)
            # TODO: obj is not defined
            url = os.getenv('API_URL') + "/v1/auth/member/invite/" + \
                str(invite.token) + "?" + querystr

            send_email_message("welcome_academy", email, {
                "email": email,
                "subject": "Welcome to Breathecode",
                "LINK": url,
                "FIST_NAME": validated_data['first_name']
            })

        return super().create({**validated_data, "email": email, "user": user, "academy": academy, "role": role, "status": status})


class StudentPOSTSerializer(serializers.ModelSerializer):
    invite = serializers.BooleanField(write_only=True, required=False)
    cohort = serializers.IntegerField(write_only=True, required=False)
    user = serializers.IntegerField(write_only=True, required=False)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ProfileAcademy
        fields = ('email', 'user', 'first_name', 'last_name',
                  'address', 'phone', 'invite', 'cohort', 'status')

    def validate(self, data):
        if 'email' in data:
            data['email'] = data['email'].lower()

        if "user" not in data:
            if "invite" not in data or data["invite"] != True:
                raise ValidationException(
                    "User does not exists, do you want to invite it?")
            elif "email" not in data:
                raise ValidationException(
                    "Please specify user id or student email")

            already = ProfileAcademy.objects.filter(
                email=data['email'], academy=self.context['academy_id']).first()
            if already:
                raise ValidationException(
                    'There is a student already in this academy, or with invitation pending')

        elif "user" in data:
            already = ProfileAcademy.objects.filter(
                user=data['user'], academy=self.context['academy_id']).first()
            if already:
                raise ValidationError(
                    'This user is already a member of this academy staff')

        return data

    def create(self, validated_data):

        academy = Academy.objects.filter(
            id=self.context.get('academy_id')).first()
        if academy is None:
            raise ValidationException("Academy not found")

        role = Role.objects.filter(slug='student').first()
        if role is None:
            raise ValidationException("Role student not found")

        user = None
        email = None
        status = "INVITED"
        if "user" in validated_data:
            user = User.objects.filter(id=validated_data["user"]).first()
            if user is None:
                raise ValidationException("User not found")
            email = user.email
            status = "ACTIVE"

        if "user" not in validated_data:
            validated_data.pop('invite')
            email = validated_data["email"]
            cohort = None
            if 'cohort' in validated_data:
                cohort = Cohort.objects.filter(
                    id=validated_data.pop('cohort')).first()

            invite = UserInvite.objects.filter(
                email=validated_data['email'], author=self.context.get('request').user).first()
            if invite is not None:
                raise ValidationException(
                    "You already invited this user, check for previous invites and resend")

            invite = UserInvite(
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                academy=academy,
                cohort=cohort,
                role=role,
                author=self.context.get('request').user,
                token=random.getrandbits(128)
            )
            invite.save()

            logger.debug("Sending invite email to "+email)

            params = {"callback": "https://learn.breatheco.de"}

            querystr = urllib.parse.urlencode(params)
            url = os.getenv('API_URL') + "/v1/auth/member/invite/" + \
                str(invite.token) + "?" + querystr

            send_email_message("welcome_academy", email, {
                "email": email,
                "subject": "Welcome to Breathecode",
                "LINK": url,
                "FIST_NAME": validated_data['first_name']
            })

        return super().create({**validated_data, "email": email, "user": user, "academy": academy, "role": role, "status": status})


class MemberPUTSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAcademy
        fields = ('user', 'role', 'academy', 'first_name',
                  'last_name', 'phone', 'address')

    def validate(self, data):

        already = ProfileAcademy.objects.filter(
            user=data['user'], academy=data['academy']).first()
        if not already:
            raise ValidationError('User not found on this particular academy')

        return data


class AuthSerializer(serializers.Serializer):
    email = serializers.EmailField(label="Email")
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            email = email.lower()
            user = User.objects.filter(
                Q(email__iexact=email) | Q(username=email)).first()
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
