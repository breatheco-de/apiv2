"""
This file will test branches of the ai_context instead of the whole content
"""

import random
from unittest.mock import patch

import capyc.pytest as capy
import pytest
from aiohttp_retry import Optional

from breathecode.registry.models import Asset, AssetContext

LANG_MAP = {
    "en": "english",
    "es": "spanish",
    "it": "italian",
}


# Fixture to create an Asset instance
@pytest.fixture
def asset():
    return Asset.objects.create(slug="test-asset", title="Test Asset", status="PUBLISHED", lang="en")


# Fixture to mock the save method of AssetContext
@pytest.fixture
def mock_save(monkeypatch):
    with patch("breathecode.registry.receivers.AssetContext.save") as mock_save:
        monkeypatch.setattr(AssetContext, "save", mock_save)
        yield mock_save


# Fixture to mock the build_ai_context method of Asset
@pytest.fixture
def mock_build_ai_context(monkeypatch):
    with patch("breathecode.registry.models.Asset.build_ai_context", return_value="test-ai-context") as mock_method:
        monkeypatch.setattr(Asset, "build_ai_context", mock_method)
        yield mock_method


def test_default_branch(database: capy.Database, signals: capy.Signals):
    signals.enable("django.db.models.signals.m2m_changed")
    model = database.create(
        asset=1,
        asset_category=1,
        city=1,
        country=1,
    )

    db = database.list_of("registry.AssetContext")
    assert len(db) == 0


class TestTranslationsBranches:

    def msg1(self, asset: Asset):
        translations = ", ".join([x.title for x in asset.all_translations.all()])
        return f", and it has the following translations: {translations}. "

    def test_translations(self, database: capy.Database, signals: capy.Signals):
        signals.enable("django.db.models.signals.m2m_changed")
        model = database.create(
            asset=3,
            asset_category=1,
            city=1,
            country=1,
        )

        model.asset[0].all_translations.set([model.asset[1], model.asset[2]])

        db = database.list_of("registry.AssetContext")
        assert len(db) == 1
        asset_context = db[0]

        # integrity checks
        assert asset_context["id"] == 1
        assert asset_context["asset_id"] == 1

        ai_context = asset_context["ai_context"]

        # content checks
        assert self.msg1(model.asset[0]) in ai_context


class TestAssetsRelatedBranches:

    def msg1(self, asset: Asset):
        assets_related = ", ".join([x.slug for x in asset.assets_related.all()])
        return (
            f"In case you still need to learn more about the basics of this {asset.asset_type}, "
            "you can check these lessons, exercises, "
            f"and related projects to get ready for this content: {assets_related}. "
        )

    def test_assets_related(self, database: capy.Database, signals: capy.Signals):
        signals.enable("django.db.models.signals.m2m_changed")
        model = database.create(
            asset=3,
            asset_category=1,
            city=1,
            country=1,
        )

        model.asset[0].assets_related.set([model.asset[1], model.asset[2]])

        db = database.list_of("registry.AssetContext")
        assert len(db) == 1
        asset_context = db[0]

        # integrity checks
        assert asset_context["id"] == 1
        assert asset_context["asset_id"] == 1

        ai_context = asset_context["ai_context"]

        # content checks
        assert self.msg1(model.asset[0]) in ai_context


# technologies
class TestTechnologiesBranches:

    def msg1(self, asset: Asset):
        technologies = ", ".join([x.title for x in asset.technologies.all()])
        return f"This asset is about the following technologies: {technologies}. "

    def test_assets_related(self, database: capy.Database, signals: capy.Signals):
        signals.enable("django.db.models.signals.m2m_changed")
        model = database.create(
            asset=1,
            asset_category=1,
            asset_technology=2,
            city=1,
            country=1,
        )

        db = database.list_of("registry.AssetContext")
        assert len(db) == 1
        asset_context = db[0]

        # integrity checks
        assert asset_context["id"] == 1
        assert asset_context["asset_id"] == 1

        ai_context = asset_context["ai_context"]

        # content checks
        assert self.msg1(model.asset) in ai_context
