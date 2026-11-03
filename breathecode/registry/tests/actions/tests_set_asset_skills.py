import pytest
from django.core.cache import cache

from breathecode.registry.actions import (
    MAX_SKILLS_PER_ASSET,
    get_skills_generation,
    inherit_asset_skills,
    set_asset_skills,
)
from breathecode.registry.models import Asset, AssetErrorLog, AssetSkill
from breathecode.registry.utils import AssetErrorLogType
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
        slug: Skill.objects.create(slug=slug, name=slug.replace("-", " ").title(), domain=domain)
        for slug in ["python-loops", "python-functions", "http-basics", "sql-joins", "git-branches", "css-flexbox"]
    }


def create_asset(slug="intro-loops", lang="en", asset_type="LESSON"):
    return Asset.objects.create(slug=slug, title=slug, asset_type=asset_type, lang=lang)


def asset_skills(asset):
    return list(AssetSkill.objects.filter(asset=asset).order_by("id").values_list("skill__slug", "level"))


def error_status(asset, slug):
    return list(AssetErrorLog.objects.filter(asset=asset, slug=slug).values_list("status", flat=True))


def test_string_and_object_forms(skills):
    asset = create_asset()

    changed = set_asset_skills(asset, ["python-loops", {"slug": "python-functions", "level": "core"}])

    assert changed is True
    assert asset_skills(asset) == [("python-loops", None), ("python-functions", "core")]
    asset.refresh_from_db()
    assert asset.skills_source == "FILE"


def test_unknown_level_is_ignored(skills):
    asset = create_asset()

    set_asset_skills(asset, [{"slug": "python-loops", "level": "guru"}])

    assert asset_skills(asset) == [("python-loops", None)]


def test_duplicates_count_once(skills):
    asset = create_asset()
    raw = ["python-loops"] * 3 + ["python-functions", "http-basics", "sql-joins", "git-branches"]

    set_asset_skills(asset, raw)

    assert len(asset_skills(asset)) == MAX_SKILLS_PER_ASSET
    assert error_status(asset, AssetErrorLogType.TOO_MANY_SKILLS) == []


def test_five_skills_are_accepted(skills):
    asset = create_asset()

    set_asset_skills(asset, list(skills)[:5])

    assert len(asset_skills(asset)) == 5


def test_six_skills_are_rejected_and_previous_kept(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-loops"])

    changed = set_asset_skills(asset, list(skills))

    assert changed is False
    assert asset_skills(asset) == [("python-loops", None)]
    assert error_status(asset, AssetErrorLogType.TOO_MANY_SKILLS) == ["ERROR"]


def test_alias_slug_is_rejected_and_previous_kept(skills):
    asset = create_asset()
    set_asset_skills(asset, ["http-basics"])

    skill = skills["python-loops"]
    skill.slug = "python-iteration"
    skill.save()

    changed = set_asset_skills(asset, ["python-loops", "sql-joins"])

    assert changed is False
    assert asset_skills(asset) == [("http-basics", None)]
    log = AssetErrorLog.objects.get(asset=asset, slug=AssetErrorLogType.DEPRECATED_SKILL_SLUG)
    assert log.status == "ERROR"
    assert '"python-loops" -> "python-iteration"' in log.status_text


def test_invalid_slugs_are_partially_applied(skills):
    asset = create_asset()

    changed = set_asset_skills(asset, ["python-loops", "does-not-exist", "", 42])

    assert changed is True
    assert asset_skills(asset) == [("python-loops", None)]
    log = AssetErrorLog.objects.get(asset=asset, slug=AssetErrorLogType.INVALID_SKILL)
    assert log.status == "ERROR"
    assert "does-not-exist" in log.status_text


def test_not_a_list_is_rejected(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-loops"])

    changed = set_asset_skills(asset, "python-loops")

    assert changed is False
    assert asset_skills(asset) == [("python-loops", None)]
    assert error_status(asset, AssetErrorLogType.INVALID_SKILL) == ["ERROR"]


def test_errors_are_fixed_by_a_later_good_sync(skills):
    asset = create_asset()
    set_asset_skills(asset, list(skills))
    set_asset_skills(asset, ["python-loops", "does-not-exist"])

    set_asset_skills(asset, ["python-loops"])

    assert error_status(asset, AssetErrorLogType.TOO_MANY_SKILLS) == ["FIXED"]
    assert error_status(asset, AssetErrorLogType.INVALID_SKILL) == ["FIXED"]


def test_empty_list_clears_skills(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-loops"])

    changed = set_asset_skills(asset, [])

    assert changed is True
    assert asset_skills(asset) == []
    asset.refresh_from_db()
    assert asset.skills_source == "FILE"


def test_none_without_translations_keeps_skills(skills):
    asset = create_asset()
    set_asset_skills(asset, ["python-loops"])

    changed = set_asset_skills(asset, None)

    assert changed is False
    assert asset_skills(asset) == [("python-loops", None)]


def test_generation_only_bumps_when_skills_change(skills):
    asset = create_asset()
    initial = get_skills_generation()

    set_asset_skills(asset, ["python-loops"])
    after_change = get_skills_generation()

    set_asset_skills(asset, ["python-loops"])
    after_noop = get_skills_generation()

    assert after_change != initial
    assert after_noop == after_change


def test_generation_survives_cache_eviction(skills):
    asset = create_asset()
    get_skills_generation()
    cache.clear()

    set_asset_skills(asset, ["python-loops"])

    assert isinstance(get_skills_generation(), int)


def test_translation_without_skills_inherits(skills):
    english = create_asset("intro-loops", "en")
    spanish = create_asset("intro-loops-es", "es")
    english.all_translations.add(spanish)

    set_asset_skills(english, ["python-loops", "python-functions"])

    spanish.refresh_from_db()
    assert spanish.skills_source == "INHERITED"
    assert asset_skills(spanish) == [("python-loops", None), ("python-functions", None)]


def test_translation_synced_later_inherits(skills):
    english = create_asset("intro-loops", "en")
    spanish = create_asset("intro-loops-es", "es")
    set_asset_skills(english, ["python-loops"])
    english.all_translations.add(spanish)

    changed = set_asset_skills(spanish, None)

    assert changed is True
    assert inherit_asset_skills(spanish) is False
    assert asset_skills(spanish) == [("python-loops", None)]


def test_translation_with_own_skills_is_not_overwritten(skills):
    english = create_asset("intro-loops", "en")
    spanish = create_asset("intro-loops-es", "es")
    english.all_translations.add(spanish)
    set_asset_skills(spanish, ["python-loops"])

    set_asset_skills(english, ["python-loops", "http-basics"])

    assert asset_skills(spanish) == [("python-loops", None)]


def test_translation_mismatch_is_logged_and_fixed(skills):
    english = create_asset("intro-loops", "en")
    spanish = create_asset("intro-loops-es", "es")
    english.all_translations.add(spanish)
    set_asset_skills(spanish, ["python-loops"])

    set_asset_skills(english, ["python-loops", "http-basics"])

    assert error_status(english, AssetErrorLogType.SKILLS_TRANSLATION_MISMATCH) == ["ERROR"]

    set_asset_skills(english, ["python-loops"])

    assert error_status(english, AssetErrorLogType.SKILLS_TRANSLATION_MISMATCH) == ["FIXED"]
