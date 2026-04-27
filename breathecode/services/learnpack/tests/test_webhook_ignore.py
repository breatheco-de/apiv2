"""Unit tests for LearnPack telemetry webhook ignore rules."""

import pytest
from capyc.rest_framework.exceptions import ValidationException

import capyc.pytest as capy

from breathecode.services.learnpack.webhook_ignore import (
    LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY,
    get_telemetry_webhook_ignore_from_settings,
    should_ignore_learnpack_webhook,
    validate_telemetry_webhook_ignore_body,
)


def test_should_ignore_matches_user_id(database: capy.Database):
    model = database.create(
        country=1,
        city=1,
        academy=1,
        academy_auth_settings=1,
    )
    settings = model.academy_auth_settings
    settings.learnpack_features = {
        LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY: {"user_ids": [42]}
    }
    settings.save(update_fields=["learnpack_features"])

    ok, reason = should_ignore_learnpack_webhook(
        model.academy.id,
        {"user_id": 42, "slug": "ex", "event": "open_step"},
    )
    assert ok is True
    assert reason and "user_ids" in reason


def test_should_ignore_false_when_no_settings(database: capy.Database):
    model = database.create(country=1, city=1, academy=1)
    ok, _ = should_ignore_learnpack_webhook(model.academy.id, {"user_id": 1, "slug": "x", "event": "batch"})
    assert ok is False


def test_should_ignore_package_id(database: capy.Database):
    model = database.create(country=1, city=1, academy=1, academy_auth_settings=1)
    settings = model.academy_auth_settings
    settings.learnpack_features = {
        LEARNPACK_FEATURES_TELEMETRY_WEBHOOK_IGNORE_KEY: {"learnpack_package_ids": [7]}
    }
    settings.save(update_fields=["learnpack_features"])

    ok, reason = should_ignore_learnpack_webhook(
        model.academy.id,
        {"user_id": 1, "slug": "x", "event": "batch", "package_id": 7},
    )
    assert ok is True
    assert reason and "learnpack_package_ids" in reason


def test_validate_body_rejects_non_list_field():
    with pytest.raises(ValidationException) as exc:
        validate_telemetry_webhook_ignore_body({"user_ids": "not-a-list"})
    assert exc.value.slug == "invalid-telemetry-webhook-ignore-field"


def test_get_telemetry_webhook_ignore_from_settings_empty(database: capy.Database):
    model = database.create(country=1, city=1, academy=1, academy_auth_settings=1)
    assert get_telemetry_webhook_ignore_from_settings(model.academy_auth_settings) == {}
