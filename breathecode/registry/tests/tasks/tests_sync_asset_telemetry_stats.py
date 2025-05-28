"""
Test sync_asset_telemetry_stats task
"""

import logging
from unittest.mock import MagicMock, call, patch

import pytest
from rest_framework.test import APIClient

from breathecode.registry.tasks import sync_asset_telemetry_stats
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode


@pytest.fixture(autouse=True)
def setup(db):
    from linked_services.django.actions import reset_app_cache

    reset_app_cache()
    yield


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
def test__without_asset(bc: Breathecode, client: APIClient):
    sync_asset_telemetry_stats.delay(1)

    assert bc.database.list_of("registry.Asset") == []
    assert logging.Logger.error.call_args_list == [call("Asset with id 1 not found", exc_info=True)]


@patch("logging.Logger.warning", MagicMock())
@patch("logging.Logger.error", MagicMock())
@patch("logging.Logger.info", MagicMock())
def test__with_asset_with_no_telemetries(bc: Breathecode, client: APIClient):
    model = bc.database.create(asset={"slug": "megadeth"})

    logging.Logger.info.call_args_list = []
    sync_asset_telemetry_stats.delay(model.asset.id)

    assert bc.database.list_of("registry.Asset") == [
        bc.format.to_dict(model.asset),
    ]

    assert logging.Logger.warning.call_args_list == []
    assert logging.Logger.error.call_args_list == []
    assert logging.Logger.info.call_args_list == [
        call("Starting sync_asset_telemetry_stats for asset 1"),
        call("No telemetries found for asset megadeth"),
    ]
