import capyc.pytest as capy
import pytest
from capyc.core.managers import feature


@pytest.fixture(autouse=True)
def setup(db: None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.events.models.LiveClass._get_hash", lambda self: "abc")

    yield


class TestEverywhere:
    @pytest.mark.parametrize("data", [[], [2]])
    def test_true(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, data: list[int], fake: capy.Fake):
        model = database.create(city=1, country=1, user=1)
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": data,
                    "from_academy": [],
                    "from_cohort": [],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is True

    def test_false(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
        model = database.create(city=1, country=1, user=1)
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [1],
                    "from_academy": [],
                    "from_cohort": [],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is False


class TestAcademy:
    @pytest.mark.parametrize("data", [[], [(2, "saudi-arabia"), (1, "germany")]])
    def test_true(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, data: list[int], fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, cohort_user=1, academy={"slug": "saudi-arabia"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [],
                    "from_academy": data,
                    "from_cohort": [],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user, academy=model.academy)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is True

    def test_false(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, cohort_user=1, academy={"slug": "saudi-arabia"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [1],
                    "from_academy": [(1, "saudi-arabia")],
                    "from_cohort": [],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user, academy=model.academy)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is False


class TestCohort:
    @pytest.mark.parametrize("data", [[], [(2, "4geeks-fs-1"), (1, "4geeks-fs-2")]])
    def test_true(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, data: list[int], fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, cohort_user=1, cohort={"slug": "4geeks-fs-1"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": data,
                    "from_academy": [],
                    "from_cohort": [],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user, cohort=model.cohort)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is True

    def test_false(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, cohort_user=1, cohort={"slug": "4geeks-fs-1"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [1],
                    "from_academy": [],
                    "from_cohort": [(1, "4geeks-fs-1")],
                    "from_mentorship_service": [],
                }
            },
        )

        context = feature.context(to=key, user=model.user, cohort=model.cohort)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is False


class TestMentorshipService:
    @pytest.mark.parametrize("data", [[], [(2, "geekpal-1-1"), (1, "geekpal-2-2")]])
    def test_true(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, data: list[int], fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, mentorship_service={"slug": "geekpal-1-1"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [],
                    "from_academy": [],
                    "from_cohort": [],
                    "from_mentorship_service": data,
                }
            },
        )

        context = feature.context(to=key, user=model.user, mentorship_service=model.mentorship_service)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is True

    def test_false(self, database: capy.Database, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake):
        model = database.create(city=1, country=1, user=1, mentorship_service={"slug": "geekpal-1-1"})
        key = fake.slug()
        monkeypatch.setattr(
            "breathecode.payments.flags.blocked_user_ids",
            {
                key: {
                    "from_everywhere": [1],
                    "from_academy": [],
                    "from_cohort": [],
                    "from_mentorship_service": [(1, "geekpal-1-1")],
                }
            },
        )

        context = feature.context(to=key, user=model.user, mentorship_service=model.mentorship_service)
        res = feature.is_enabled("payments.can_access", context=context)
        assert res is False
