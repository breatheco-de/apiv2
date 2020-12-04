import serpy
from django.contrib.auth.models import User, Group
from .models import CredentialsGithub, ProfileAcademy
from django.db import models
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.db.models import Q

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

class GETProfileAcademy(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    user = UserSmallSerializer()
    academy = AcademySmallSerializer()
    role = RoleSmallSerializer()
    created_at = serpy.Field()

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

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAcademy
        fields = ('user', 'role', 'academy')

class StaffPOSTSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileAcademy
        fields = ('user', 'role', 'academy')

    def validate(self, data):

        in_academy = ProfileAcademy.objects.filter(user=data['user'],academy=data['academy']).first()
        if not in_academy:
            raise ValidationError("You don't have access to create staff under this academy")
        # the user cannot vote to the same entity within 5 minutes
        already = ProfileAcademy.objects.filter(user=data['user'],academy=data['academy']).first()
        if already:
            raise ValidationError('This user is already a member of this academy staff')

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
            user = User.objects.filter(Q(email=email) | Q(username=email)).first()
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
