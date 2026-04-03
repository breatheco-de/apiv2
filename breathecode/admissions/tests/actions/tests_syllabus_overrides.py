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


def test_resolve_syllabus_json_with_prefixed_macro_reference():
    micro = {
        "days": [
            {"id": 1, "lessons": [], "quizzes": [], "replits": [], "assignments": [{"slug": "old-project"}]}
        ]
    }
    macro = {
        "days": [],
        "0:web-ui-fundamentals-with-tailwind.v2": {"days": [{"assignments": [{"slug": "new-project"}]}]},
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


def test_test_syllabus_accepts_existing_prefixed_reference(database: capy.Database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "front-end"},
        syllabus_version={"version": 2, "json": {"days": []}},
    )

    payload = {
        "0:front-end.v2": {
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


def test_test_syllabus_accepts_sparse_override_days_inside_reference(database: capy.Database):
    """Reference `*.vN` blocks are partial patches; modules need not list all asset keys."""
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "macro-syllabus"},
        syllabus_version={"version": 2, "json": {"days": []}},
    )

    payload = {
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ],
        "macro-syllabus.v2": {
            "days": [
                {
                    "assignments": [
                        {"slug": "only-project", "title": "Only override assignments"},
                    ]
                }
            ]
        },
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert result.errors == []

def test_test_syllabus_override_allows_null_and_empty_object_placeholders(database: capy.Database):
    """Overrides should allow placeholders by index: null / {} mean 'no change'."""
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "macro-syllabus-2"},
        syllabus_version={"version": 1, "json": {"days": []}},
    )

    payload = {
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ],
        "macro-syllabus-2.v1": {
            "days": [
                {
                    "lessons": [None, {}, {"slug": "keep-your-projects", "title": "Keep your projects"}],
                }
            ]
        },
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert result.errors == []

def test_test_syllabus_rejects_self_reference_override():
    payload = {
        "slug": "same-syllabus",
        "version": 2,
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ],
        "same-syllabus.v2": {"days": [{}]},
    }

    result = test_syllabus(payload, academy_id=1)
    assert any("cannot override itself" in e.lower() for e in result.errors)


def test_test_syllabus_rejects_prefixed_self_reference_override():
    payload = {
        "slug": "same-syllabus",
        "version": 2,
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [],
                "assignments": [],
            }
        ],
        "0:same-syllabus.v2": {"days": [{}]},
    }

    result = test_syllabus(payload, academy_id=1)
    assert any("cannot override itself" in e.lower() for e in result.errors)


def test_test_syllabus_rejects_duplicate_canonical_references(database: capy.Database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "front-end"},
        syllabus_version={"version": 2, "json": {"days": []}},
    )

    payload = {
        "front-end.v2": {"days": []},
        "0:front-end.v2": {"days": []},
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert any("duplicated" in e.lower() and "front-end.v2" in e for e in result.errors)


def test_test_syllabus_root_days_still_require_all_asset_lists():
    """Root `days` remain strict: each module must include lessons, quizzes, replits, assignments."""
    payload = {
        "days": [
            {
                "id": 1,
                "assignments": [],
            }
        ]
    }

    result = test_syllabus(payload)
    assert any("Missing lessons property on module 1" in e for e in result.errors)
    assert any("Missing quizzes property on module 1" in e for e in result.errors)
