import capyc.django.serializer as capy

from breathecode.admissions.models import Country
from breathecode.authenticate.serializers import CapyAppCountrySerializer


def test_is_capy_serializer():
    serializer = CapyAppCountrySerializer()
    assert isinstance(serializer, capy.Serializer)


def test_fields():
    assert CapyAppCountrySerializer.fields == {
        "default": ("code", "name"),
    }


def test_filters():
    assert CapyAppCountrySerializer.filters == (
        "code",
        "name",
    )


def test_path():
    assert CapyAppCountrySerializer.path == "/v1/auth/app/country"


def test_model():
    assert CapyAppCountrySerializer.model == Country


def test_references():
    serializer = CapyAppCountrySerializer()

    result = {}
    for field in dir(serializer):
        if field.startswith("_"):
            continue

        if isinstance(x := getattr(serializer, field), capy.Serializer):
            result[field] = x.__module__ + "." + x.__class__.__name__

    assert result == {}
