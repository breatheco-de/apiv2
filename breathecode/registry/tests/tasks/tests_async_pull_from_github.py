from unittest.mock import MagicMock, patch

from breathecode.registry.tasks import async_pull_from_github


@patch("breathecode.registry.tasks.pull_from_github", MagicMock())
@patch("breathecode.registry.tasks.log_pull_outcome_from_db", MagicMock())
@patch("breathecode.registry.tasks.async_pull_project_dependencies.delay", MagicMock())
@patch("breathecode.registry.tasks.async_regenerate_asset_readme.delay", MagicMock())
def test_webhook_pull_queues_same_clean_as_academy_action(db):
    from breathecode.registry.models import Asset
    from breathecode.registry import tasks

    Asset.objects.create(
        slug="introduction-to-vps-for-beginners-en",
        asset_type="LESSON",
        title="Introduction to VPS",
        sync_status="OK",
    )

    result = async_pull_from_github(
        "introduction-to-vps-for-beginners-en",
        source_webhook_id=42,
        source_commit_sha="abc123",
    )

    assert result is True
    tasks.async_regenerate_asset_readme.delay.assert_called_once_with("introduction-to-vps-for-beginners-en")
    tasks.async_pull_project_dependencies.delay.assert_called_once_with("introduction-to-vps-for-beginners-en")


@patch("breathecode.registry.tasks.pull_from_github", MagicMock())
@patch("breathecode.registry.tasks.log_pull_outcome_from_db", MagicMock())
@patch("breathecode.registry.tasks.async_pull_project_dependencies.delay", MagicMock())
@patch("breathecode.registry.tasks.async_regenerate_asset_readme.delay", MagicMock())
def test_non_webhook_pull_does_not_queue_clean(db):
    from breathecode.registry.models import Asset
    from breathecode.registry import tasks

    Asset.objects.create(
        slug="manual-pull",
        asset_type="LESSON",
        title="Manual pull",
        sync_status="OK",
    )

    result = async_pull_from_github("manual-pull")

    assert result is True
    tasks.async_regenerate_asset_readme.delay.assert_not_called()
    tasks.async_pull_project_dependencies.delay.assert_called_once_with("manual-pull")


@patch("breathecode.registry.tasks.pull_from_github", MagicMock())
@patch("breathecode.registry.tasks.log_pull_outcome_from_db", MagicMock())
@patch("breathecode.registry.tasks.async_pull_project_dependencies.delay", MagicMock())
@patch("breathecode.registry.tasks.async_regenerate_asset_readme.delay", MagicMock())
def test_failed_webhook_pull_does_not_queue_clean(db):
    from breathecode.registry.models import Asset
    from breathecode.registry import tasks

    Asset.objects.create(
        slug="broken-lesson",
        asset_type="LESSON",
        title="Broken lesson",
        sync_status="ERROR",
    )

    result = async_pull_from_github("broken-lesson", source_webhook_id=42)

    assert result is False
    tasks.async_regenerate_asset_readme.delay.assert_not_called()
    tasks.async_pull_project_dependencies.delay.assert_not_called()


@patch("breathecode.registry.tasks.pull_from_github", MagicMock())
@patch("breathecode.registry.tasks.log_pull_outcome_from_db", MagicMock())
@patch("breathecode.registry.tasks.async_pull_project_dependencies.delay", MagicMock())
@patch("breathecode.registry.tasks.async_regenerate_asset_readme.delay", MagicMock())
def test_missing_asset_does_not_queue_clean(db):
    from breathecode.registry import tasks

    result = async_pull_from_github("does-not-exist", source_webhook_id=42)

    assert result is False
    tasks.async_regenerate_asset_readme.delay.assert_not_called()
    tasks.async_pull_project_dependencies.delay.assert_not_called()
