"""Tests for Asset learn.json mapping: apply_learn_config, to_learn_config, learn_config_to_metadata, sync_fields_to_learn_config."""

import pytest
from breathecode.registry.models import Asset, AssetTechnology


@pytest.mark.django_db
def test_learn_config_to_metadata_project():
    """Asset.learn_config_to_metadata returns flat metadata for PROJECT config."""
    config = {
        "projectType": "project",
        "slug": "my-project",
        "title": "My Project",
        "description": "A project",
        "difficulty": "easy",
        "duration": 2,
        "technologies": ["python", "django"],
        "preview": "https://example.com/preview.png",
    }
    meta = Asset.learn_config_to_metadata(config, lang=None)
    assert meta["asset_type"] == "PROJECT"
    assert meta["slug"] == "my-project"
    assert meta["title"] == "My Project"
    assert meta["description"] == "A project"
    assert meta["difficulty"] == "easy"
    assert meta["duration"] == 2
    assert meta["technologies"] == ["python", "django"]
    assert meta["preview"] == "https://example.com/preview.png"


@pytest.mark.django_db
def test_learn_config_to_metadata_exercise():
    """Asset.learn_config_to_metadata returns asset_type EXERCISE for exercise config."""
    config = {"projectType": "exercise", "slug": "ex-1", "title": "Exercise 1"}
    meta = Asset.learn_config_to_metadata(config)
    assert meta["asset_type"] == "EXERCISE"
    assert meta["slug"] == "ex-1"
    assert meta["title"] == "Exercise 1"


@pytest.mark.django_db
def test_learn_config_to_metadata_multilang():
    """Asset.learn_config_to_metadata uses lang for multi-language title/description."""
    config = {
        "title": {"us": "US Title", "es": "Título ES"},
        "description": {"us": "US Desc", "es": "Desc ES"},
    }
    meta_us = Asset.learn_config_to_metadata(config, lang="us")
    assert meta_us["title"] == "US Title"
    assert meta_us["description"] == "US Desc"
    meta_es = Asset.learn_config_to_metadata(config, lang="es")
    assert meta_es["title"] == "Título ES"
    assert meta_es["description"] == "Desc ES"


@pytest.mark.django_db
def test_apply_learn_config_updates_asset():
    """apply_learn_config applies config to asset and saves."""
    tech = AssetTechnology.get_or_create("python")
    asset = Asset.objects.create(
        slug="test-exercise",
        title="Old Title",
        description="Old Desc",
        asset_type="EXERCISE",
        lang="us",
        preview="https://example.com/old.png",
    )
    config = {
        "slug": "test-exercise",
        "title": "New Title",
        "description": "New Desc",
        "preview": "https://example.com/new.png",
        "difficulty": "EASY",
        "duration": 3,
        "technologies": ["python"],
        "projectType": "tutorial",
        "grading": "incremental",
    }
    result = asset.apply_learn_config(config)
    assert result is asset
    asset.refresh_from_db()
    assert asset.title == "New Title"
    assert asset.description == "New Desc"
    assert asset.preview == "https://example.com/new.png"
    assert asset.difficulty == "EASY"
    assert asset.duration == 3
    assert list(asset.technologies.values_list("slug", flat=True)) == ["python"]


@pytest.mark.django_db
def test_apply_learn_config_raises_for_quiz():
    """apply_learn_config raises for QUIZ asset type."""
    asset = Asset.objects.create(
        slug="quiz-asset",
        title="Quiz",
        asset_type="QUIZ",
        lang="us",
        preview="https://example.com/p.png",
    )
    with pytest.raises(Exception, match="Can only process exercise and project config"):
        asset.apply_learn_config({"title": "Q", "preview": "https://x.com/p.png"})


@pytest.mark.django_db
def test_to_learn_config_builds_dict():
    """to_learn_config builds learn.json-shaped dict from asset."""
    asset = Asset.objects.create(
        slug="proj-1",
        title="Project One",
        description="A project",
        asset_type="PROJECT",
        lang="us",
        preview="https://example.com/p.png",
        difficulty="EASY",
        duration=2,
    )
    config = asset.to_learn_config()
    assert config["slug"] == "proj-1"
    assert config["title"] == "Project One" or "us" in config["title"]
    assert config["preview"] == "https://example.com/p.png"
    assert config["difficulty"] == "EASY"
    assert config["duration"] == 2
    assert config["projectType"] == "project"
    assert "technologies" in config


@pytest.mark.django_db
def test_sync_fields_to_learn_config_patches_config():
    """sync_fields_to_learn_config returns config with updated fields patched."""
    asset = Asset.objects.create(
        slug="ex-1",
        title="Ex",
        asset_type="EXERCISE",
        lang="us",
        preview="https://example.com/p.png",
        config={
            "slug": "ex-1",
            "title": {"us": "Old"},
            "description": {"us": "Old desc"},
            "preview": "https://example.com/p.png",
            "difficulty": "easy",
        },
    )
    updated = Asset.sync_fields_to_learn_config(
        asset,
        {"title": "New Title", "difficulty": "HARD"},
    )
    assert updated is not None
    assert updated["title"]["us"] == "New Title"
    assert updated["title"]["en"] == "New Title"
    assert updated["difficulty"] == "HARD"
    assert updated["description"]["us"] == "Old desc"


@pytest.mark.django_db
def test_sync_fields_to_learn_config_returns_none_when_no_config():
    """sync_fields_to_learn_config returns None when asset has no config."""
    asset = Asset.objects.create(
        slug="no-config",
        title="No Config",
        asset_type="EXERCISE",
        lang="us",
        preview="https://example.com/p.png",
        config=None,
    )
    assert Asset.sync_fields_to_learn_config(asset, {"title": "X"}) is None
