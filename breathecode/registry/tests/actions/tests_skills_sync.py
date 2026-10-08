import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.utils import timezone

from breathecode.registry.actions import pull_github_lesson, pull_quiz_asset, set_asset_skills
from breathecode.registry.models import Asset, AssetSkill
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
        slug: Skill.objects.create(slug=slug, name=slug, domain=domain)
        for slug in ["python-loops", "python-functions", "http-basics"]
    }


def create_asset(**kwargs):
    data = {
        "slug": "intro-loops",
        "title": "Intro loops",
        "asset_type": "EXERCISE",
        "lang": "en",
        "readme_url": "https://github.com/4geeks/intro-loops/blob/main/README.md",
        **kwargs,
    }
    return Asset.objects.create(**data)


def asset_skill_slugs(asset):
    return list(AssetSkill.objects.filter(asset=asset).order_by("id").values_list("skill__slug", flat=True))


def blob(content: str):
    return MagicMock(content=base64.b64encode(content.encode("utf-8")).decode("utf-8"))


def github_mock():
    repo = MagicMock()
    repo.raw_data = {"private": False}
    github = MagicMock()
    github.get_repo.return_value = repo
    return github


def test_apply_learn_config_syncs_skills(skills):
    asset = create_asset()

    asset.apply_learn_config({"title": "Loops", "preview": "https://x.test/p.png", "skills": ["python-loops"]})

    assert asset_skill_slugs(asset) == ["python-loops"]
    assert asset.skills_source == "FILE"


def test_apply_learn_config_without_skills_keeps_previous(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-loops"])

    asset.apply_learn_config({"title": "Loops", "preview": "https://x.test/p.png"})

    assert asset_skill_slugs(asset) == ["python-loops"]


def test_to_learn_config_emits_skills_from_db(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-functions", "python-loops"])

    config = asset.to_learn_config()

    assert config["skills"] == ["python-functions", "python-loops"]


def test_to_learn_config_keeps_raw_skills_from_file(skills):
    raw = [{"slug": "python-loops", "level": "core"}, "unknown-skill"]
    asset = create_asset(config={"skills": raw})
    set_asset_skills(asset, raw)

    config = asset.to_learn_config()

    assert config["skills"] == raw


def test_to_learn_config_without_skills_source_does_not_emit(skills):
    asset = create_asset()

    assert "skills" not in asset.to_learn_config()


def test_learn_config_to_metadata_includes_skills():
    assert Asset.learn_config_to_metadata({"skills": ["python-loops"]})["skills"] == ["python-loops"]


def test_pull_lesson_reads_skills_even_without_override_meta(skills):
    asset = create_asset(asset_type="LESSON", last_synch_at=timezone.now())
    readme = "---\ntitle: New title\nskills:\n  - python-loops\n  - slug: http-basics\n    level: core\n---\n\n# Hello"

    with patch("breathecode.registry.actions.get_blob_content", MagicMock(return_value=blob(readme))):
        pull_github_lesson(github_mock(), asset, override_meta=False)

    assert asset.title == "Intro loops"
    assert list(AssetSkill.objects.filter(asset=asset).order_by("id").values_list("skill__slug", "level")) == [
        ("python-loops", None),
        ("http-basics", "core"),
    ]


def test_pull_lesson_without_skills_keeps_previous(skills):
    asset = create_asset(asset_type="LESSON", last_synch_at=timezone.now())
    set_asset_skills(asset, ["python-loops"])

    with patch("breathecode.registry.actions.get_blob_content", MagicMock(return_value=blob("# Hello"))):
        pull_github_lesson(github_mock(), asset, override_meta=False)

    assert asset_skill_slugs(asset) == ["python-loops"]


@pytest.mark.parametrize(
    "quiz",
    [
        {"info": {"name": "Loops quiz", "skills": ["python-loops"]}, "questions": []},
        {"info": {"name": "Loops quiz"}, "skills": ["python-loops"], "questions": []},
    ],
)
def test_pull_quiz_syncs_skills(skills, quiz):
    asset = create_asset(asset_type="QUIZ")

    with (
        patch("breathecode.registry.actions.get_blob_content", MagicMock(return_value=blob(json.dumps(quiz)))),
        patch("breathecode.registry.actions.create_from_asset", MagicMock(side_effect=lambda x: x)),
    ):
        pull_quiz_asset(github_mock(), asset)

    assert asset_skill_slugs(asset) == ["python-loops"]


def quiz_assessment():
    return MagicMock(to_json=MagicMock(side_effect=lambda: {"info": {"name": "Loops quiz"}, "questions": []}))


def test_generate_quiz_json_keeps_raw_skills_from_file(skills):
    raw = [{"slug": "python-loops", "level": "core"}]
    asset = create_asset(asset_type="QUIZ", config={"info": {"skills": raw}})
    set_asset_skills(asset, raw)

    with patch.object(Asset, "assessment", quiz_assessment()):
        config = asset.generate_quiz_json()

    assert config["info"]["skills"] == raw


def test_generate_quiz_json_emits_skills_from_db(skills):
    asset = create_asset(asset_type="QUIZ")
    set_asset_skills(asset, ["python-loops"])

    with patch.object(Asset, "assessment", quiz_assessment()):
        config = asset.generate_quiz_json()

    assert config["info"]["skills"] == ["python-loops"]


def test_generate_quiz_json_without_skills_source_does_not_emit(skills):
    asset = create_asset(asset_type="QUIZ")

    with patch.object(Asset, "assessment", quiz_assessment()):
        config = asset.generate_quiz_json()

    assert "skills" not in config["info"]
