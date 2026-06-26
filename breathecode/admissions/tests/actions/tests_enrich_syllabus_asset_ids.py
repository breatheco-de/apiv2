import capyc.pytest as capy
import pytest

from ...actions import enrich_syllabus_asset_ids


@pytest.fixture(autouse=True)
def setup(db: None):
    yield


def test_enrich_root_days_adds_asset_ids(database: capy.Database):
    model = database.create(
        asset={"slug": "my-lesson"},
    )
    syllabus_json = {
        "days": [
            {
                "lessons": [{"slug": "my-lesson"}],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ]
    }

    enriched = enrich_syllabus_asset_ids(syllabus_json)

    assert enriched["days"][0]["lessons"][0]["id"] == model.asset.id
    assert "id" not in syllabus_json["days"][0]["lessons"][0]


def test_enrich_reference_override_key(database: capy.Database):
    model = database.create(
        asset={"slug": "override-project"},
    )
    syllabus_json = {
        "days": [],
        "macro-syllabus.v2": {
            "days": [{"assignments": [{"slug": "override-project"}]}],
        },
    }

    enriched = enrich_syllabus_asset_ids(syllabus_json)

    assert enriched["macro-syllabus.v2"]["days"][0]["assignments"][0]["id"] == model.asset.id


def test_enrich_resolves_asset_alias_slug(database: capy.Database):
    model = database.create(
        asset={"slug": "canonical-slug"},
        asset_alias={"slug": "alias-slug"},
    )
    syllabus_json = {
        "days": [{"lessons": [{"slug": "alias-slug"}], "quizzes": [], "replits": [], "assignments": []}]
    }

    enriched = enrich_syllabus_asset_ids(syllabus_json)

    assert enriched["days"][0]["lessons"][0]["id"] == model.asset.id


def test_enrich_removes_stale_id_for_missing_slug():
    syllabus_json = {
        "days": [{"lessons": [{"slug": "missing-slug", "id": 999}], "quizzes": [], "replits": [], "assignments": []}]
    }

    enriched = enrich_syllabus_asset_ids(syllabus_json)

    assert "id" not in enriched["days"][0]["lessons"][0]


def test_enrich_skips_placeholders_and_deleted():
    syllabus_json = {
        "days": [
            {
                "lessons": [None, {}, {"status": "DELETED"}],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ]
    }

    enriched = enrich_syllabus_asset_ids(syllabus_json)

    assert enriched["days"][0]["lessons"] == [None, {}, {"status": "DELETED"}]


def test_enrich_is_idempotent(database: capy.Database):
    model = database.create(asset={"slug": "lesson-a"})
    syllabus_json = {"days": [{"lessons": [{"slug": "lesson-a"}], "quizzes": [], "replits": [], "assignments": []}]}

    first = enrich_syllabus_asset_ids(syllabus_json)
    second = enrich_syllabus_asset_ids(first)

    assert second == first
    assert second["days"][0]["lessons"][0]["id"] == model.asset.id


def test_test_syllabus_reports_slug_id_mismatch(database: capy.Database):
    from ...actions import test_syllabus

    model = database.create(
        asset={"slug": "lesson-a"},
        asset_alias={"slug": "lesson-a"},
    )

    payload = {
        "days": [
            {
                "id": 1,
                "lessons": [{"slug": "lesson-a", "id": model.asset.id + 1}],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ]
    }

    result = test_syllabus(payload, validate_assets=True)
    assert any("does not match slug" in error for error in result.errors)
