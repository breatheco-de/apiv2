from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
from breathecode.registry.models import Asset
from breathecode.authenticate.models import User


class CleanAssetsCommandTest(TestCase):
    """Test cases for the clean_assets management command."""

    def setUp(self):
        self.bc = Breathecode()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_command_help(self):
        """Test that the command shows help information."""
        with self.assertRaises(SystemExit):
            call_command('clean_assets', '--help')

    def test_command_with_no_assets(self):
        """Test command when no assets exist."""
        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets')
            mock_clean.delay.assert_not_called()

    def test_command_with_assets_no_readme(self):
        """Test command with assets that have no readme content."""
        # Create asset without readme
        asset = Asset.objects.create(
            slug="test-asset",
            title="Test Asset",
            asset_type="PROJECT",
            readme="",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets')
            mock_clean.delay.assert_not_called()

    def test_command_with_assets_with_readme(self):
        """Test command with assets that have readme content."""
        # Create asset with readme
        asset = Asset.objects.create(
            slug="test-asset",
            title="Test Asset",
            asset_type="PROJECT",
            readme="Some readme content",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets')
            mock_clean.delay.assert_called_once_with(asset.slug)

    def test_command_with_asset_type_filter(self):
        """Test command with asset type filter."""
        # Create assets of different types
        project_asset = Asset.objects.create(
            slug="project-asset",
            title="Project Asset",
            asset_type="PROJECT",
            readme="Project readme",
            owner=self.user
        )
        lesson_asset = Asset.objects.create(
            slug="lesson-asset",
            title="Lesson Asset",
            asset_type="LESSON",
            readme="Lesson readme",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--asset-type', 'PROJECT')
            mock_clean.delay.assert_called_once_with(project_asset.slug)

    def test_command_with_status_filter(self):
        """Test command with status filter."""
        # Create assets with different statuses
        published_asset = Asset.objects.create(
            slug="published-asset",
            title="Published Asset",
            asset_type="PROJECT",
            readme="Published readme",
            status="PUBLISHED",
            owner=self.user
        )
        draft_asset = Asset.objects.create(
            slug="draft-asset",
            title="Draft Asset",
            asset_type="PROJECT",
            readme="Draft readme",
            status="DRAFT",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--status', 'PUBLISHED')
            mock_clean.delay.assert_called_once_with(published_asset.slug)

    def test_command_with_lang_filter(self):
        """Test command with language filter."""
        # Create assets with different languages
        en_asset = Asset.objects.create(
            slug="en-asset",
            title="English Asset",
            asset_type="PROJECT",
            readme="English readme",
            lang="en",
            owner=self.user
        )
        es_asset = Asset.objects.create(
            slug="es-asset",
            title="Spanish Asset",
            asset_type="PROJECT",
            readme="Spanish readme",
            lang="es",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--lang', 'en')
            mock_clean.delay.assert_called_once_with(en_asset.slug)

    def test_command_with_all_flag(self):
        """Test command with --all flag to process all assets."""
        # Create assets with recent cleaning
        recent_asset = Asset.objects.create(
            slug="recent-asset",
            title="Recent Asset",
            asset_type="PROJECT",
            readme="Recent readme",
            last_cleaning_at=timezone.now(),
            owner=self.user
        )
        old_asset = Asset.objects.create(
            slug="old-asset",
            title="Old Asset",
            asset_type="PROJECT",
            readme="Old readme",
            last_cleaning_at=timezone.now() - timezone.timedelta(days=2),
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--all')
            # Should process both assets
            self.assertEqual(mock_clean.delay.call_count, 2)

    def test_command_with_force_flag(self):
        """Test command with --force flag."""
        # Create asset with recent cleaning
        asset = Asset.objects.create(
            slug="force-asset",
            title="Force Asset",
            asset_type="PROJECT",
            readme="Force readme",
            last_cleaning_at=timezone.now(),
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--force')
            mock_clean.delay.assert_called_once_with(asset.slug)

    def test_command_with_dry_run(self):
        """Test command with --dry-run flag."""
        # Create asset
        asset = Asset.objects.create(
            slug="dry-run-asset",
            title="Dry Run Asset",
            asset_type="PROJECT",
            readme="Dry run readme",
            owner=self.user
        )

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--dry-run')
            # Should not call the task
            mock_clean.delay.assert_not_called()

    def test_command_with_batch_size_and_delay(self):
        """Test command with custom batch size and delay."""
        # Create multiple assets
        assets = []
        for i in range(15):
            asset = Asset.objects.create(
                slug=f"batch-asset-{i}",
                title=f"Batch Asset {i}",
                asset_type="PROJECT",
                readme=f"Batch readme {i}",
                owner=self.user
            )
            assets.append(asset)

        with patch('breathecode.registry.tasks.async_regenerate_asset_readme') as mock_clean:
            call_command('clean_assets', '--batch-size', '5', '--delay', '0.1')
            # Should process all 15 assets
            self.assertEqual(mock_clean.delay.call_count, 15)
