import capyc.django.serializer as capy

from breathecode.admissions.models import City
from breathecode.authenticate.serializers import CapyAppCitySerializer, CapyAppCountrySerializer


def test_is_capy_serializer():
    serializer = CapyAppCitySerializer()
    assert isinstance(serializer, capy.Serializer)


def test_fields():
    assert CapyAppCitySerializer.fields == {
        "default": ("id", "name", "country"),
        "country": ("country[]",),
    }


def test_filters():
    assert CapyAppCitySerializer.filters == ("name",)


def test_path():
    assert CapyAppCitySerializer.path == "/v1/auth/app/city"


def test_model():
    assert CapyAppCitySerializer.model == City


def test_references():
    serializer = CapyAppCitySerializer()

    result = {}
    for field in dir(serializer):
        if field.startswith("_"):
            continue

        if isinstance(x := getattr(serializer, field), capy.Serializer):
            result[field] = x.__module__ + "." + x.__class__.__name__

    assert result == {"country": "breathecode.authenticate.serializers.CapyAppCountrySerializer"}
