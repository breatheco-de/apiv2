import pytest

from breathecode.payments.serializers import GetPlanSerializer


pytestmark = pytest.mark.django_db


def test_get_features_returns_none_without_plan_features(database):
    model = database.create(plan=1)

    data = GetPlanSerializer(model.plan, many=False, lang="en").data

    assert data["features"] is None


def test_get_features_returns_language_list(database):
    bullets = {
        "en": [{"title": "AI", "description": "English description"}],
        "es": [{"title": "IA", "description": "Descripcion en espanol"}],
    }
    model = database.create(plan=1, plan_features={"bullets": bullets})

    data_es = GetPlanSerializer(model.plan, many=False, lang="es").data
    data_en = GetPlanSerializer(model.plan, many=False, lang="en").data

    assert data_es["features"] == [{"title": "IA", "description": "Descripcion en espanol"}]
    assert data_en["features"] == [{"title": "AI", "description": "English description"}]


def test_get_features_falls_back_to_en(database):
    bullets = {
        "en": [{"title": "AI", "description": "English description"}],
    }
    model = database.create(plan=1, plan_features={"bullets": bullets})

    data = GetPlanSerializer(model.plan, many=False, lang="es").data

    assert data["features"] == [{"title": "AI", "description": "English description"}]
