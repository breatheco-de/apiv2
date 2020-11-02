import serpy
from django.contrib.auth.models import User, Group
from .models import CredentialsGithub
from django.db import models
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.db.models import Q

class GithubSmallSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    avatar_url = serpy.Field()
    name = serpy.Field()

# Create your models here.
class UserSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    email = serpy.Field()
    first_name = serpy.Field()
    last_name = serpy.Field()
    github = serpy.MethodField()

    def get_github(self, obj):
        github = CredentialsGithub.objects.get(user=obj.id)
        return GithubSmallSerializer(github).data


class GroupSerializer(serpy.Serializer):
    """The serializer schema definition."""
    # Use a Field subclass like IntField if you need more validation.
    id = serpy.Field()
    name = serpy.Field()

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
