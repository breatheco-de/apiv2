from unittest.mock import MagicMock, patch

import pytest

from breathecode.admissions.models import Cohort
from breathecode.events.models import Event
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

# Activate signals for testing
pytestmark = pytest.mark.usefixtures("enable_signals")


@pytest.fixture(autouse=True)
def enable_signals_fixture(enable_signals):
    enable_signals(
        "django.db.models.signals.post_save",
        "django.db.models.signals.post_delete",
        "breathecode.commons.signals.update_cache",
    )
    yield


# Patch the cache enabled check for all tests in this module
@pytest.fixture(autouse=True)
def patch_cache_check(monkeypatch):
    monkeypatch.setattr("breathecode.commons.receivers.is_cache_enabled", lambda: True)
    yield


@patch("breathecode.commons.actions.clean_cache")
def test_cohort_save_triggers_action(mock_action: MagicMock, bc: Breathecode, database):
    """
    Verify that saving a Cohort instance triggers actions.clean_cache with Cohort model.
    """
    model = database.create(cohort=1, city=1, country=1)

    # Assert action was called with Cohort after creation
    # Note: database.create might trigger saves on related models too.
    # We check specifically for the call with Cohort.
    mock_action.assert_any_call(Cohort)
    initial_call_count = mock_action.call_count

    # Reset mock and save again
    mock_action.reset_mock()
    model.cohort.name = "Updated Name"
    model.cohort.save()

    # Assert action was called once with Cohort after update
    mock_action.assert_called_once_with(Cohort)


@patch("breathecode.commons.actions.clean_cache")
def test_cohort_delete_triggers_action(mock_action: MagicMock, bc: Breathecode, database):
    """
    Verify that deleting a Cohort instance triggers actions.clean_cache with Cohort model.
    """
    model = database.create(cohort=1, city=1, country=1)

    # Clear mock calls from creation
    mock_action.reset_mock()

    # Delete the instance
    model.cohort.delete()

    # Assert action was called once with Cohort after deletion
    mock_action.assert_called_once_with(Cohort)


@patch("breathecode.commons.actions.clean_cache")
def test_event_save_triggers_action(mock_action: MagicMock, bc: Breathecode, database):
    """
    Verify that saving an Event instance triggers actions.clean_cache with Event model.
    """
    model = database.create(event=1)

    # Assert action was called with Event after creation
    mock_action.assert_any_call(Event)
    initial_call_count = mock_action.call_count

    # Reset mock and save again
    mock_action.reset_mock()
    model.event.title = "Updated Title"
    model.event.save()

    # Assert action was called once with Event after update
    mock_action.assert_called_once_with(Event)


@patch("breathecode.commons.actions.clean_cache")
def test_event_delete_triggers_action(mock_action: MagicMock, bc: Breathecode, database):
    """
    Verify that deleting an Event instance triggers actions.clean_cache with Event model.
    """
    model = database.create(event=1)

    # Clear mock calls from creation
    mock_action.reset_mock()

    # Delete the instance
    model.event.delete()

    # Assert action was called once with Event after deletion
    mock_action.assert_called_once_with(Event)
