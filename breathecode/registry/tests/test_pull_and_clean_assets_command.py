from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.registry.models import Asset
from breathecode.authenticate.models import User


class PullAndCleanAssetsCommandTest(TestCase):
    """Test the pull_and_clean_assets management command."""

    def setUp(self):
        self.bc = Breathecode()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_command_help(self):
        """Test that the command shows help when called with --help."""
        with self.assertRaises(SystemExit):
            call_command("pull_and_clean_assets", "--help")

    def test_command_no_assets_found(self):
        """Test command when no assets match the criteria."""
        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets")
                
                # Verify no tasks were called
                mock_pull.delay.assert_not_called()
                mock_clean.delay.assert_not_called()

    def test_command_with_assets(self):
        """Test command with assets that need processing."""
        # Create test assets
        asset1 = Asset.objects.create(
            slug="test-asset-1",
            title="Test Asset 1",
            asset_type="PROJECT",
            readme_url="https://github.com/test/repo1/blob/main/README.md",
            owner=self.user
        )
        
        asset2 = Asset.objects.create(
            slug="test-asset-2",
            title="Test Asset 2",
            asset_type="EXERCISE",
            readme_url="https://github.com/test/repo2/blob/main/README.md",
            owner=self.user
        )

        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets")
                
                # Verify tasks were called for both assets
                self.assertEqual(mock_pull.delay.call_count, 2)
                self.assertEqual(mock_clean.delay.call_count, 2)
                
                # Verify correct parameters
                mock_pull.delay.assert_any_call(
                    "test-asset-1",
                    user_id=self.user.id,
                    override_meta=False
                )
                mock_pull.delay.assert_any_call(
                    "test-asset-2",
                    user_id=self.user.id,
                    override_meta=False
                )

    def test_command_with_filters(self):
        """Test command with asset type filter."""
        # Create assets of different types
        Asset.objects.create(
            slug="test-project",
            title="Test Project",
            asset_type="PROJECT",
            readme_url="https://github.com/test/project/blob/main/README.md",
            owner=self.user
        )
        
        Asset.objects.create(
            slug="test-lesson",
            title="Test Lesson",
            asset_type="LESSON",
            readme_url="https://github.com/test/lesson/blob/main/README.md",
            owner=self.user
        )

        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets", "--asset-type", "PROJECT")
                
                # Verify only PROJECT assets were processed
                self.assertEqual(mock_pull.delay.call_count, 1)
                mock_pull.delay.assert_called_with(
                    "test-project",
                    user_id=self.user.id,
                    override_meta=False
                )

    def test_command_dry_run(self):
        """Test command in dry-run mode."""
        Asset.objects.create(
            slug="test-asset",
            title="Test Asset",
            asset_type="PROJECT",
            readme_url="https://github.com/test/repo/blob/main/README.md",
            owner=self.user
        )

        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets", "--dry-run")
                
                # Verify no tasks were called in dry-run mode
                mock_pull.delay.assert_not_called()
                mock_clean.delay.assert_not_called()

    def test_command_force_option(self):
        """Test command with force option."""
        asset = Asset.objects.create(
            slug="test-asset",
            title="Test Asset",
            asset_type="PROJECT",
            readme_url="https://github.com/test/repo/blob/main/README.md",
            owner=self.user,
            last_synch_at=timezone.now()  # Recently synced
        )

        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets", "--force")
                
                # Verify task was called with force=True
                mock_pull.delay.assert_called_with(
                    "test-asset",
                    user_id=self.user.id,
                    override_meta=True
                )

    def test_command_custom_delay(self):
        """Test command with custom delay."""
        Asset.objects.create(
            slug="test-asset",
            title="Test Asset",
            asset_type="PROJECT",
            readme_url="https://github.com/test/repo/blob/main/README.md",
            owner=self.user
        )

        with patch("time.sleep") as mock_sleep:
            with patch("breathecode.registry.tasks.async_pull_from_github"):
                with patch("breathecode.registry.tasks.async_regenerate_asset_readme"):
                    call_command("pull_and_clean_assets", "--delay", "2.5")
                    
                    # Verify sleep was called with custom delay
                    mock_sleep.assert_called_with(2.5)

    def test_command_batch_processing(self):
        """Test command with custom batch size."""
        # Create multiple assets
        for i in range(15):
            Asset.objects.create(
                slug=f"test-asset-{i}",
                title=f"Test Asset {i}",
                asset_type="PROJECT",
                readme_url=f"https://github.com/test/repo{i}/blob/main/README.md",
                owner=self.user
            )

        with patch("breathecode.registry.tasks.async_pull_from_github") as mock_pull:
            with patch("breathecode.registry.tasks.async_regenerate_asset_readme") as mock_clean:
                call_command("pull_and_clean_assets", "--batch-size", "5")
                
                # Verify all assets were processed
                self.assertEqual(mock_pull.delay.call_count, 15)
                self.assertEqual(mock_clean.delay.call_count, 15)
