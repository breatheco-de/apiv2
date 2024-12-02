"""
This file will test branches of the ai_context instead of the whole content
"""

import random
from typing import Optional

import capyc.pytest as capy
import pytest

from breathecode.registry.models import Asset

LANG_MAP = {
    "en": "english",
    "es": "spanish",
    "it": "italian",
}


@pytest.mark.parametrize("asset_type", ["PROJECT", "LESSON", "EXERCISE", "QUIZ", "VIDEO", "ARTICLE"])
def test_default_branch(database: capy.Database, signals: capy.Signals, asset_type: str):
    signals.enable("breathecode.registry.signals.asset_saved")
    model = database.create(
        asset={
            "lang": random.choice([*LANG_MAP.keys()]),
            "asset_type": asset_type,
            "external": False,
            "interactive": False,
            "gitpod": False,
        },
        asset_category=1,
        city=1,
        country=1,
    )

    lang = LANG_MAP[model.asset.lang]
    db = database.list_of("registry.AssetContext")

    assert len(db) == 1
    asset_context = db[0]

    # integrity checks
    assert asset_context["id"] == 1
    assert asset_context["asset_id"] == 1

    ai_context = asset_context["ai_context"]

    # content checks
    assert f"This {model.asset.asset_type} about {model.asset.title} is written in {lang}" in ai_context
    assert (
        f"It's category related is (what type of skills the student will get) {model.asset_category.title}"
        in ai_context
    )


class TestAssetTypeBranches:

    def msg1(self):
        return "This project should be delivered by sending a github repository URL. "

    def msg2(self, asset: Asset):
        return f"This project should be delivered by adding a file of one of these types: {asset.delivery_formats}. "

    def msg3(self, asset: Asset):
        return f"This project should be delivered with a URL that follows this format: {asset.delivery_regex_url}. "

    @pytest.mark.parametrize("asset_type", ["LESSON", "EXERCISE", "QUIZ", "VIDEO", "ARTICLE"])
    def test_is_not_project(self, database: capy.Database, signals: capy.Signals, asset_type: str):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "lang": random.choice([*LANG_MAP.keys()]),
                "asset_type": asset_type,
                "external": False,
                "interactive": False,
                "gitpod": False,
            },
            asset_category=1,
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
        assert self.msg1() not in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) not in ai_context

    @pytest.mark.parametrize("asset_type", ["PROJECT"])
    @pytest.mark.parametrize("delivery_instructions", ["", None])
    def test_is_project__no_delivery_instructions(
        self, database: capy.Database, signals: capy.Signals, asset_type: str, delivery_instructions: str
    ):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "lang": random.choice([*LANG_MAP.keys()]),
                "asset_type": asset_type,
                "delivery_instructions": delivery_instructions,
            },
            asset_category=1,
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
        assert self.msg1() in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) not in ai_context

    @pytest.mark.parametrize("asset_type", ["PROJECT"])
    def test_is_project__with_delivery_instructions__with_delivery_formats(
        self, database: capy.Database, signals: capy.Signals, asset_type: str, fake: capy.Fake
    ):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "lang": random.choice([*LANG_MAP.keys()]),
                "asset_type": asset_type,
                "delivery_instructions": fake.text(),
                "delivery_formats": ",".join(["zip", "rar"]),
            },
            asset_category=1,
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
        assert self.msg1() not in ai_context
        assert self.msg2(model.asset) in ai_context
        assert self.msg3(model.asset) not in ai_context

    @pytest.mark.parametrize("asset_type", ["PROJECT"])
    def test_is_project__with_delivery_regex_url(
        self, database: capy.Database, signals: capy.Signals, asset_type: str, fake: capy.Fake
    ):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "lang": random.choice([*LANG_MAP.keys()]),
                "asset_type": asset_type,
                "delivery_instructions": None,
                "delivery_regex_url": fake.url(),
            },
            asset_category=1,
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
        assert self.msg1() in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) in ai_context


class TestSolutionUrlBranches:

    def msg1(self, asset: Asset):
        return f", and it has a solution code this link is: {asset.solution_url}. "

    def test_not_solution_url(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset=1,
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_solution_url(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_url": fake.url(),
            },
            asset_category=1,
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


class TestSolutionVideoUrlBranches:

    def msg1(self, asset: Asset):
        return f", and it has a video solution this link is {asset.solution_video_url}. "

    def test_not_solution_video_url(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset=1,
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_solution_video_url(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_video_url": fake.url(),
            },
            asset_category=1,
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


class TestExternalBranches:

    def msg1(self, asset: Asset):
        return f"This asset is external, which means it opens outside 4geeks. "

    def test_not_external(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "external": False,
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_external(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_video_url": fake.url(),
                "external": True,
            },
            asset_category=1,
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


class TestInteractiveBranches:

    def msg1(self):
        return "This asset opens on LearnPack so it has a step-by-step of the exercises that you should follow. "

    def msg2(self, asset: Asset):
        return f"This {asset.asset_type} has videos on each step. "

    def msg3(self, asset: Asset):
        return f"This {asset.asset_type} has a code solution on each step. "

    def test_not_interactive(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "interactive": False,
                "with_solutions": False,
                "with_video": False,
            },
            asset_category=1,
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
        assert self.msg1() not in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) not in ai_context

    def test_interactive(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_video_url": fake.url(),
                "interactive": True,
            },
            asset_category=1,
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
        assert self.msg1() in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) not in ai_context

    def test_interactive__with_video(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_video_url": fake.url(),
                "interactive": True,
                "with_video": True,
                "with_solutions": False,
            },
            asset_category=1,
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
        assert self.msg1() in ai_context
        assert self.msg2(model.asset) in ai_context
        assert self.msg3(model.asset) not in ai_context

    def test_interactive__with_solutions(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "solution_video_url": fake.url(),
                "interactive": True,
                "with_solutions": True,
                "with_video": False,
            },
            asset_category=1,
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
        assert self.msg1() in ai_context
        assert self.msg2(model.asset) not in ai_context
        assert self.msg3(model.asset) in ai_context


class TestGitpodBranches:

    def msg1(self, asset: Asset):
        return (
            f"This {asset.asset_type} can be opened both locally or with click and code (This "
            "way you don't have to install anything and it will open automatically on gitpod or github codespaces). "
        )

    def test_not_gitpod(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "gitpod": False,
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_gitpod(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "gitpod": True,
            },
            asset_category=1,
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


class TestDurationBranches:

    def msg1(self, asset: Asset):
        return f"This {asset.asset_type} will last {asset.duration} hours. "

    @pytest.mark.parametrize("duration", [None, 0])
    def test_not_duration(self, database: capy.Database, signals: capy.Signals, duration: Optional[int]):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "duration": duration,
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_duration(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "duration": random.randint(1, 10),
            },
            asset_category=1,
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


class TestDifficultyBranches:

    def msg1(self, asset: Asset):
        return f"Its difficulty is considered as {asset.difficulty}. "

    @pytest.mark.parametrize("difficulty", [None, ""])
    def test_not_difficulty(self, database: capy.Database, signals: capy.Signals, difficulty: Optional[str]):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "difficulty": difficulty,
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_difficulty(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "difficulty": random.choice(["HARD", "INTERMEDIATE", "EASY", "BEGINNER"]),
            },
            asset_category=1,
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


class TestReadmeBranches:

    def msg1(self, asset: Asset):
        return f"The markdown file with the instructions of this {asset.asset_type} is the following: {asset.html}."

    def msg2(self, asset: Asset):
        return f"The markdown file with the content of this {asset.asset_type} is the following: {asset.html}."

    @pytest.mark.parametrize("readme", [None, ""])
    def test_not_readme(self, database: capy.Database, signals: capy.Signals, readme: Optional[str]):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "readme": readme,
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context
        assert self.msg2(model.asset) not in ai_context

    def test_readme__project(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "html": fake.text(),
                "asset_type": "PROJECT",
            },
            asset_category=1,
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
        assert self.msg2(model.asset) not in ai_context

    def test_readme__anything_else(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset={
                "html": fake.text(),
                "asset_type": random.choice(["LESSON", "EXERCISE", "QUIZ", "VIDEO", "ARTICLE"]),
            },
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context
        assert self.msg2(model.asset) in ai_context


class TestSupersededByBranches:

    def msg1(self, asset: Asset):
        title = ""
        if asset.superseded_by:
            title = asset.superseded_by.title

        return f"This {asset.asset_type} has a previous version which is: {title}. "

    def test_no_superseded_by(self, database: capy.Database, signals: capy.Signals):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset=1,
            asset_category=1,
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
        assert self.msg1(model.asset) not in ai_context

    def test_superseded_by(self, database: capy.Database, signals: capy.Signals, fake: capy.Fake):
        signals.enable("breathecode.registry.signals.asset_saved")
        model = database.create(
            asset=2,
            asset_category=1,
            city=1,
            country=1,
        )

        model.asset[0].superseded_by = model.asset[1]
        model.asset[0].save()
        db = database.list_of("registry.AssetContext")
        assert len(db) == 2
        asset_context = db[0]

        # integrity checks
        assert asset_context["id"] == 1
        assert asset_context["asset_id"] == 1

        ai_context = asset_context["ai_context"]

        # content checks
        assert self.msg1(model.asset[0]) in ai_context
