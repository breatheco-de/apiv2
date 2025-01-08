import capyc.django.serializer as capy

from breathecode.authenticate.models import Academy
from breathecode.authenticate.serializers import CapyAppAcademySerializer


def test_is_capy_serializer():
    serializer = CapyAppAcademySerializer()
    assert isinstance(serializer, capy.Serializer)


def test_fields():
    assert CapyAppAcademySerializer.fields == {
        "default": ("id", "name", "slug", "legal_name", "status"),
        "meta": ("white_labeled", "available_as_saas", "is_hidden_on_prework", "timezone"),
        "marketing": ("active_campaign_slug", "logistical_information"),
        "urls": ("logo_url", "icon_url", "website_url", "white_label_url"),
        "emails": ("marketing_email", "feedback_email"),
        "social": ("linkedin_url", "youtube_url"),
        "location": ("city[]", "country[]", "latitude", "longitude", "zip_code", "street_address"),
        "timestamps": ("created_at", "updated_at"),
    }


def test_filters():
    assert CapyAppAcademySerializer.filters == (
        "name",
        "slug",
        "legal_name",
        "status",
        "created_at",
        "available_as_saas",
    )


def test_path():
    assert CapyAppAcademySerializer.path == "/v1/auth/app/academy"


def test_model():
    assert CapyAppAcademySerializer.model == Academy


def test_references():
    serializer = CapyAppAcademySerializer()

    result = {}
    for field in dir(serializer):
        if field.startswith("_"):
            continue

        if isinstance(x := getattr(serializer, field), capy.Serializer):
            result[field] = x.__module__ + "." + x.__class__.__name__

    assert result == {
        "city": "breathecode.authenticate.serializers.CapyAppCitySerializer",
        "country": "breathecode.authenticate.serializers.CapyAppCountrySerializer",
    }
