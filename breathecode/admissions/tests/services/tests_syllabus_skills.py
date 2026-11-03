from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from breathecode.admissions.models import Syllabus, SyllabusVersion
from breathecode.admissions.services import skills as skills_service
from breathecode.admissions.services.skills import get_syllabus_skills
from breathecode.registry.actions import set_asset_skills
from breathecode.registry.models import Asset, AssetAlias
from breathecode.talent_development.models import Skill, SkillDomain


@pytest.fixture(autouse=True)
def clear_skills_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def skills(db):
    domain = SkillDomain.objects.create(name="Programming", slug="programming", description="")
    return {
        slug: Skill.objects.create(slug=slug, name=slug.title(), domain=domain)
        for slug in ["python-loops", "python-functions", "http-basics"]
    }


def create_asset(slug, asset_type="LESSON", difficulty=None, skill_slugs=None):
    asset = Asset.objects.create(slug=slug, title=slug, asset_type=asset_type, lang="en", difficulty=difficulty)
    if skill_slugs is not None:
        set_asset_skills(asset, skill_slugs)
    return asset


def create_version(days):
    syllabus = Syllabus.objects.create(slug="full-stack", name="Full Stack")
    return SyllabusVersion.objects.create(syllabus=syllabus, version=1, json={"days": days})


def test_union_of_asset_skills(skills):
    create_asset("loops-lesson", "LESSON", "BEGINNER", ["python-loops"])
    create_asset("loops-exercise", "EXERCISE", "HARD", ["python-loops", "python-functions"])
    create_asset("http-project", "PROJECT", "INTERMEDIATE", ["http-basics"])
    create_asset("no-skills-lesson", "LESSON")

    version = create_version(
        [
            {
                "position": 1,
                "lessons": [{"slug": "loops-lesson"}, {"slug": "no-skills-lesson"}],
                "replits": [{"slug": "loops-exercise", "mandatory": False}],
            },
            {
                "position": 2,
                "assignments": [{"slug": "http-project", "mandatory": False}],
                "quizzes": [{"slug": "missing-quiz"}],
            },
        ]
    )

    result = get_syllabus_skills(version)

    assert result == {
        "syllabus": "full-stack",
        "version": 1,
        "total_assets": 4,
        "unmapped_assets": 1,
        "unresolved_slugs": ["missing-quiz"],
        "skills": [
            {
                "slug": "python-loops",
                "name": "Python-Loops",
                "domain": "programming",
                "by_asset_type": {"LESSON": 1, "EXERCISE": 1},
                "max_difficulty": "HARD",
                "days": [1],
                "mandatory": True,
                "asset_count": 2,
            },
            {
                "slug": "http-basics",
                "name": "Http-Basics",
                "domain": "programming",
                "by_asset_type": {"PROJECT": 1},
                "max_difficulty": "INTERMEDIATE",
                "days": [2],
                "mandatory": False,
                "asset_count": 1,
            },
            {
                "slug": "python-functions",
                "name": "Python-Functions",
                "domain": "programming",
                "by_asset_type": {"EXERCISE": 1},
                "max_difficulty": "HARD",
                "days": [1],
                "mandatory": False,
                "asset_count": 1,
            },
        ],
    }


def test_asset_alias_and_slug_count_once(skills):
    asset = create_asset("loops-lesson", skill_slugs=["python-loops"])
    AssetAlias.objects.create(slug="old-loops-lesson", asset=asset)

    version = create_version(
        [
            {"position": 1, "lessons": [{"slug": "old-loops-lesson"}]},
            {"position": 2, "lessons": [{"slug": "loops-lesson"}]},
        ]
    )

    result = get_syllabus_skills(version)

    assert result["total_assets"] == 1
    assert result["skills"][0]["asset_count"] == 1
    assert result["skills"][0]["days"] == [1, 2]


def test_deleted_markers_and_empty_items_are_ignored(skills):
    create_asset("loops-lesson", skill_slugs=["python-loops"])
    version = create_version([{"lessons": [{"slug": "loops-lesson", "status": "DELETED"}, {}, None]}])

    result = get_syllabus_skills(version)

    assert result["total_assets"] == 0
    assert result["skills"] == []


def test_result_is_cached_until_skills_change(skills):
    asset = create_asset("loops-lesson", skill_slugs=["python-loops"])
    version = create_version([{"position": 1, "lessons": [{"slug": "loops-lesson"}]}])

    compute = MagicMock(wraps=skills_service.compute_syllabus_skills)
    with patch.object(skills_service, "compute_syllabus_skills", compute):
        get_syllabus_skills(version)
        get_syllabus_skills(version)
        assert compute.call_count == 1

        set_asset_skills(asset, ["python-loops", "http-basics"])
        result = get_syllabus_skills(version)

    assert compute.call_count == 2
    assert [x["slug"] for x in result["skills"]] == ["http-basics", "python-loops"]


def test_cache_is_invalidated_when_syllabus_version_changes(skills):
    create_asset("loops-lesson", skill_slugs=["python-loops"])
    create_asset("http-lesson", skill_slugs=["http-basics"])
    version = create_version([{"position": 1, "lessons": [{"slug": "loops-lesson"}]}])

    get_syllabus_skills(version)
    version.json = {"days": [{"position": 1, "lessons": [{"slug": "http-lesson"}]}]}
    version.save()

    result = get_syllabus_skills(version)

    assert [x["slug"] for x in result["skills"]] == ["http-basics"]
