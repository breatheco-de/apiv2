import capyc.django.serializer as capy

from breathecode.authenticate.models import ProfileAcademy
from breathecode.authenticate.serializers import CapyAppProfileAcademySerializer


def test_is_capy_serializer():
    serializer = CapyAppProfileAcademySerializer()
    assert isinstance(serializer, capy.Serializer)


def test_fields():
    assert CapyAppProfileAcademySerializer.fields == {
        "default": (
            "id",
            "first_name",
            "last_name",
            "status",
            "email",
            "phone",
            "user",
            "academy",
        ),
        "address": ("address",),
        "academy": ("academy[]",),
        "user": ("user[]",),
        "timestamps": (
            "created_at",
            "updated_at",
        ),
    }


def test_filters():
    assert CapyAppProfileAcademySerializer.filters == ("status", "email", "id")


def test_path():
    assert CapyAppProfileAcademySerializer.path == "/v1/auth/app/student"


def test_model():
    assert CapyAppProfileAcademySerializer.model == ProfileAcademy


def test_references():
    serializer = CapyAppProfileAcademySerializer()

    result = {}
    for field in dir(serializer):
        if field.startswith("_"):
            continue

        if isinstance(x := getattr(serializer, field), capy.Serializer):
            result[field] = x.__module__ + "." + x.__class__.__name__

    assert result == {
        "academy": "breathecode.authenticate.serializers.CapyAppAcademySerializer",
        "user": "breathecode.authenticate.serializers.CapyAppUserSerializer",
    }
