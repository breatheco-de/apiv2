import os
from typing import Callable, TypedDict, Unpack
from unittest.mock import PropertyMock

import pytest

from capyc.core.managers import feature
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "capyc.core.managers.feature._flags",
        PropertyMock(
            return_value={
                "availability": {},
                "variant": {},
            }
        ),
    )
    yield


class Meta(TypedDict):
    frontend: bool
    default: bool


type MetaBuilder = Callable[..., None]


@pytest.fixture
def availability():

    def wrapper(**meta: Unpack[Meta]):

        @feature.availability("test.availability", **meta)
        def enable_activity() -> bool:
            env = os.getenv("MY_ENV")
            if env in feature.TRUE:
                return True

            if env in feature.FALSE:
                return False

        feature.add(enable_activity)

    yield wrapper


@pytest.fixture
def variant():

    def wrapper(**meta: Unpack[Meta]):

        @feature.variant("test.variant", **meta)
        def get_color() -> bool:
            env = os.getenv("MY_ENV")
            if env == "1":
                return "red"

            if env == "2":
                return "blue"

        feature.add(get_color)

    yield wrapper


class TestAvailability:
    def test_env_is_none(self, availability: MetaBuilder) -> None:
        availability()
        value = feature.is_enabled("test.availability")
        assert value is False

    @pytest.mark.parametrize("default", [True, False])
    def test_env_is_none__default_in_decorator(self, availability: MetaBuilder, default: bool) -> None:
        availability(default=default)
        value = feature.is_enabled("test.availability")
        assert value is default

    @pytest.mark.parametrize("default", [True, False])
    def test_env_is_none__default_in_fn(self, availability: MetaBuilder, default: bool) -> None:
        availability()
        value = feature.is_enabled("test.availability", default=default)
        assert value is default

    @pytest.mark.parametrize("default", [True, False])
    def test_env_is_none__both_defaults(self, variant: MetaBuilder, default: bool) -> None:
        variant(default=not default)
        value = feature.is_enabled("test.availability", default=default)
        assert value is default

    @pytest.mark.parametrize("env", feature.FALSE)
    def test_env_is_false(self, monkeypatch: pytest.MonkeyPatch, availability: MetaBuilder, env: str) -> None:
        availability()
        monkeypatch.setenv("MY_ENV", env)
        value = feature.is_enabled("test.availability")
        assert value is False

    @pytest.mark.parametrize("env", feature.TRUE)
    def test_env_is_true(self, monkeypatch: pytest.MonkeyPatch, availability: MetaBuilder, env: str) -> None:
        availability()
        monkeypatch.setenv("MY_ENV", env)
        value = feature.is_enabled("test.availability")
        assert value is True


class TestVariant:
    def test_env_is_none(self, variant: MetaBuilder) -> None:
        variant()
        value = feature.get_variant("test.variant")
        assert value == "unknown"

    @pytest.mark.parametrize("default", ["hello", "world"])
    def test_env_is_none__default_in_decorator(self, variant: MetaBuilder, default: bool) -> None:
        variant(default=default)
        value = feature.get_variant("test.variant")
        assert value is default

    @pytest.mark.parametrize("default", ["hello", "world"])
    def test_env_is_none__default_in_fn(self, variant: MetaBuilder, default: bool) -> None:
        variant()
        value = feature.get_variant("test.variant", default=default)
        assert value is default

    @pytest.mark.parametrize("default", ["hello", "world"])
    def test_env_is_none__both_defaults(self, variant: MetaBuilder, default: bool, fake: capy.Fake) -> None:
        variant(default=fake.slug())
        value = feature.get_variant("test.variant", default=default)
        assert value is default

    def test_env_eq_1(self, monkeypatch: pytest.MonkeyPatch, variant: MetaBuilder) -> None:
        variant()
        monkeypatch.setenv("MY_ENV", "1")
        value = feature.get_variant("test.variant")
        assert value == "red"

    def test_env_eq_2(self, monkeypatch: pytest.MonkeyPatch, variant: MetaBuilder) -> None:
        variant()
        monkeypatch.setenv("MY_ENV", "2")
        value = feature.get_variant("test.variant")
        assert value == "blue"
