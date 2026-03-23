import capyc.pytest as capy
import pytest

from ...actions import apply_reference_override, resolve_syllabus_json, test_syllabus


@pytest.fixture(autouse=True)
def setup(db: None):
    yield


def test_apply_reference_override_merges_by_position_and_deletes_assets():
    base = {
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [],
                "assignments": [
                    {"slug": "project-1", "title": "Project 1"},
                    {"slug": "project-2", "title": "Project 2"},
                ],
            }
        ]
    }
    override = {
        "days": [
            {
                "assignments": [
                    {"status": "DELETED"},
                    {"slug": "another-project", "title": "Another Project"},
                ]
            }
        ]
    }

    merged = apply_reference_override(base, override)

    assert merged["days"][0]["assignments"] == [{"slug": "another-project", "title": "Another Project"}]


def test_resolve_syllabus_json_with_macro_reference():
    micro = {
        "days": [
            {"id": 1, "lessons": [], "quizzes": [], "replits": [], "assignments": [{"slug": "old-project"}]}
        ]
    }
    macro = {
        "days": [],
        "web-ui-fundamentals-with-tailwind.v2": {"days": [{"assignments": [{"slug": "new-project"}]}]},
    }

    resolved = resolve_syllabus_json(
        micro,
        macro_syllabus_json=macro,
        syllabus_slug="web-ui-fundamentals-with-tailwind",
        syllabus_version=2,
    )

    assert resolved["days"][0]["assignments"][0]["slug"] == "new-project"


def test_test_syllabus_accepts_existing_reference(database: capy.Database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "front-end"},
        syllabus_version={"version": 2, "json": {"days": []}},
    )

    payload = {
        "front-end.v2": {
            "days": [],
        }
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert result.errors == []


def test_test_syllabus_reports_missing_reference():
    payload = {
        "front-end.v999": {
            "days": [],
        }
    }

    result = test_syllabus(payload, academy_id=1)
    assert any("Missing referenced syllabus version `front-end.v999`" in error for error in result.errors)
