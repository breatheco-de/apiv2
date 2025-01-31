import capyc.django.serializer as capy

from breathecode.authenticate.models import User
from breathecode.authenticate.serializers import CapyAppUserSerializer


def test_is_capy_serializer():
    serializer = CapyAppUserSerializer()
    assert isinstance(serializer, capy.Serializer)


def test_fields():
    assert CapyAppUserSerializer.fields == {
        "default": (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
        ),
        "timestamps": (
            "date_joined",
            "last_login",
        ),
    }


def test_filters():
    assert CapyAppUserSerializer.filters == (
        "id",
        "username",
        "first_name",
        "last_name",
        "email",
        "date_joined",
        "last_login",
    )


def test_path():
    assert CapyAppUserSerializer.path == "/v1/auth/app/user"


def test_model():
    assert CapyAppUserSerializer.model == User


def test_references():
    serializer = CapyAppUserSerializer()

    result = {}
    for field in dir(serializer):
        if field.startswith("_"):
            continue

        if isinstance(x := getattr(serializer, field), capy.Serializer):
            result[field] = x.__module__ + "." + x.__class__.__name__

    assert result == {}
