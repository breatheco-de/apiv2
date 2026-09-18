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


def test_apply_reference_override_replaces_asset_when_slug_changes():
    base = {
        "days": [
            {
                "id": 1,
                "lessons": [],
                "quizzes": [],
                "replits": [
                    {
                        "id": 3230,
                        "slug": "html-fundamentals-building-web-structure-en",
                        "title": "HTML Fundamentals: Building Web Structure",
                        "mandatory": True,
                        "translations": {
                            "us": {
                                "slug": "html-fundamentals-building-web-structure-en",
                                "title": "HTML Fundamentals: Building Web Structure",
                            }
                        },
                    }
                ],
                "assignments": [],
            }
        ]
    }
    override = {
        "days": [
            {
                "replits": [
                    {
                        "id": 3395,
                        "slug": "token-efficiency-with-coding-agents-mastering-a-en",
                        "title": "Token Efficiency with Coding Agents: Mastering Auto Mode",
                        "mandatory": True,
                    }
                ]
            }
        ]
    }

    merged = apply_reference_override(base, override)

    assert merged["days"][0]["replits"] == [
        {
            "id": 3395,
            "slug": "token-efficiency-with-coding-agents-mastering-a-en",
            "title": "Token Efficiency with Coding Agents: Mastering Auto Mode",
            "mandatory": True,
        }
    ]


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


def test_apply_reference_override_merges_display_order_from_macro():
    base = {
        "days": [
            {
                "id": 1,
                "lessons": [{"slug": "lesson-a", "title": "Lesson A", "display_order": 5}],
                "quizzes": [],
                "replits": [
                    {"slug": "exercise-a", "title": "Exercise A", "display_order": 0},
                    {"slug": "exercise-b", "title": "Exercise B", "display_order": 1},
                ],
                "assignments": [{"slug": "project-a", "title": "Project A", "display_order": 6}],
            }
        ]
    }
    override = {
        "days": [
            {
                "lessons": [{"slug": "lesson-a", "display_order": 2}],
                "replits": [
                    {"display_order": 0},
                    {"slug": "exercise-b", "display_order": 4},
                ],
                "assignments": [{"display_order": 3}],
            }
        ]
    }

    merged = apply_reference_override(base, override)
    day = merged["days"][0]

    assert day["lessons"][0]["display_order"] == 2
    assert day["replits"][0]["display_order"] == 0
    assert day["replits"][0]["slug"] == "exercise-a"
    assert day["replits"][1]["display_order"] == 4
    assert day["assignments"][0]["display_order"] == 3
    assert day["assignments"][0]["slug"] == "project-a"


def test_test_syllabus_accepts_display_order_only_patch_in_reference(database: capy.Database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "macro-syllabus-do"},
        syllabus_version={"version": 1, "json": {"days": []}},
    )

    payload = {
        "days": [{"id": 1, "lessons": [], "quizzes": [], "replits": [], "assignments": []}],
        "macro-syllabus-do.v1": {
            "days": [
                {
                    "replits": [
                        {"display_order": 0},
                        {"slug": "exercise-b", "display_order": 2},
                    ]
                }
            ]
        },
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert result.errors == []


def test_test_syllabus_rejects_invalid_display_order_patch_in_reference(database: capy.Database):
    model = database.create(
        city=1,
        country=1,
        academy=1,
        syllabus={"slug": "macro-syllabus-do-invalid"},
        syllabus_version={"version": 1, "json": {"days": []}},
    )

    payload = {
        "days": [{"id": 1, "lessons": [], "quizzes": [], "replits": [], "assignments": []}],
        "macro-syllabus-do-invalid.v1": {
            "days": [{"replits": [{"display_order": -1}]}]
        },
    }

    result = test_syllabus(payload, academy_id=model.academy.id)
    assert any("Missing slug" in error for error in result.errors)
