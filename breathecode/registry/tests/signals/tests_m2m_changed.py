"""
This file will test branches of the ai_context instead of the whole content
"""

import capyc.pytest as capy

from breathecode.registry.models import Asset


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
            "you can check these lessons, and exercises, "
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
