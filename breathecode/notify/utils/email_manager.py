import json
import logging
import os
from pathlib import Path
from typing import Optional

from capyc.rest_framework.exceptions import ValidationException
from django.template.loader import get_template

logger = logging.getLogger(__name__)


class EmailManagerClass:
    """
    Manager for notification templates and email previews.
    Loads notification registry from JSON files and provides preview functionality.
    """

    _registry = None
    _registry_path = None

    def __init__(self):
        """Initialize the EmailManager and load the notification registry."""
        self._registry_path = Path(__file__).parent.parent / "registry"
        self._load_registry()

    def _load_registry(self):
        """
        Load all notification JSON files from the registry directory.
        Caches the loaded notifications for performance.
        """
        if self._registry is not None:
            return

        self._registry = {}

        if not self._registry_path.exists():
            logger.warning(f"Notification registry directory not found: {self._registry_path}")
            return

        # Scan directory for JSON files
        for json_file in self._registry_path.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    notification = json.load(f)

                # Validate that slug matches filename
                slug = notification.get("slug")
                if not slug:
                    logger.error(f"Missing slug in {json_file.name}")
                    continue

                if f"{slug}.json" != json_file.name:
                    logger.error(f"Slug mismatch in {json_file.name}: expected {slug}.json")
                    continue

                self._registry[slug] = notification
                logger.debug(f"Loaded notification: {slug}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {json_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")

        logger.info(f"Loaded {len(self._registry)} notifications from registry")

    def get_notification(self, slug: str) -> Optional[dict]:
        """
        Get notification configuration for a specific slug.

        Args:
            slug: The notification slug

        Returns:
            dict: Notification configuration or None if not found
        """
        return self._registry.get(slug)

    def list_notifications(self, category: Optional[str] = None, channel: Optional[str] = None) -> list[dict]:
        """
        List all available notifications with optional filters.

        Args:
            category: Filter by category (e.g., 'authentication', 'academy')
            channel: Filter by channel availability (e.g., 'email', 'slack')

        Returns:
            list: List of notification configurations
        """
        notifications = list(self._registry.values())

        if category:
            notifications = [n for n in notifications if n.get("category") == category]

        if channel:
            notifications = [n for n in notifications if channel in n.get("channels", {})]

        return notifications

    def get_categories(self) -> list[str]:
        """
        Get all unique notification categories.

        Returns:
            list: List of category strings
        """
        categories = set(n.get("category") for n in self._registry.values() if n.get("category"))
        return sorted(categories)

    def validate_notification(self, slug: str) -> bool:
        """
        Check if a notification exists in the registry and has an email channel.

        Args:
            slug: The notification slug

        Returns:
            bool: True if notification exists and has email channel configured
        """
        if slug not in self._registry:
            return False
        
        notification = self._registry[slug]
        channels = notification.get("channels", {})
        
        # Validate that email channel exists
        return "email" in channels

    def require_notification(self, slug: str) -> dict:
        """
        Get a notification from the registry or raise an exception if not found or invalid.
        
        This method is useful when you want to enforce that a notification must be properly
        registered before use, providing better error handling and notifications.

        Args:
            slug: The notification slug

        Returns:
            dict: The notification configuration

        Raises:
            ValidationException: If notification not found or doesn't have email channel
        """
        if slug not in self._registry:
            raise ValidationException(
                f"Notification template '{slug}' not found in registry. "
                f"Please add a JSON file at breathecode/notify/registry/{slug}.json",
                slug="notification-not-registered"
            )
        
        notification = self._registry[slug]
        channels = notification.get("channels", {})
        
        if "email" not in channels:
            raise ValidationException(
                f"Notification template '{slug}' does not have an email channel configured",
                slug="notification-missing-email-channel"
            )
        
        return notification

    def get_available_variables(self, slug: str, academy=None) -> dict:
        """
        Get all available variables for a notification template.

        Args:
            slug: The notification slug
            academy: Optional Academy model instance for academy-specific variables

        Returns:
            dict: Variables organized by type (default, template_specific, academy_specific)
        """
        notification = self.get_notification(slug)
        if not notification:
            raise ValidationException(f"Notification '{slug}' not found in registry")

        # Default variables always available
        default_vars = {
            "API_URL": os.environ.get("API_URL", ""),
            "COMPANY_NAME": os.environ.get("COMPANY_NAME", ""),
            "COMPANY_CONTACT_URL": os.environ.get("COMPANY_CONTACT_URL", ""),
            "COMPANY_LEGAL_NAME": os.environ.get("COMPANY_LEGAL_NAME", ""),
            "COMPANY_ADDRESS": os.environ.get("COMPANY_ADDRESS", ""),
            "style__success": "#99ccff",
            "style__danger": "#ffcccc",
            "style__secondary": "#ededed",
        }

        # Template-specific variables from notification config
        template_vars = {}
        for var in notification.get("variables", []):
            template_vars[var["name"]] = {
                "description": var.get("description", ""),
                "source": var.get("source", ""),
                "example": var.get("example", ""),
                "required": var.get("required", False),
            }

        # Academy-specific variables if academy provided
        academy_vars = {}
        if academy:
            academy_vars = {
                "COMPANY_INFO_EMAIL": academy.feedback_email if hasattr(academy, "feedback_email") else None,
                "COMPANY_LEGAL_NAME": (
                    academy.legal_name or academy.name if hasattr(academy, "legal_name") else academy.name
                ),
                "COMPANY_LOGO": academy.logo_url if hasattr(academy, "logo_url") else None,
                "COMPANY_NAME": academy.name if hasattr(academy, "name") else None,
            }

        return {"default": default_vars, "template_specific": template_vars, "academy_specific": academy_vars}

    def get_template_preview(self, slug: str, academy=None, channels=None) -> dict:
        """
        Generate a preview of the notification template with variables intact.

        Args:
            slug: The notification slug
            academy: Optional Academy model instance for branding
            channels: Optional list of channels to preview (default: all available)

        Returns:
            dict: Preview data with template sources and variable metadata
        """
        notification = self.get_notification(slug)
        if not notification:
            raise ValidationException(f"Notification '{slug}' not found in registry")

        # Determine which channels to preview
        available_channels = notification.get("channels", {})
        if channels:
            # Filter to requested channels
            channels_to_preview = {ch: available_channels[ch] for ch in channels if ch in available_channels}
        else:
            # Preview all available channels
            channels_to_preview = available_channels

        # Build preview for each channel
        channel_previews = {}

        for channel_name, channel_config in channels_to_preview.items():
            template_path = channel_config.get("template_path")

            if channel_name == "email":
                # Load HTML and text templates
                try:
                    html_template = get_template(f"{template_path}.html")
                    html_source = html_template.template.source

                    try:
                        txt_template = get_template(f"{template_path}.txt")
                        txt_source = txt_template.template.source
                    except Exception:
                        txt_source = None

                    channel_previews["email"] = {
                        "html": html_source,
                        "text": txt_source,
                        "subject": channel_config.get("default_subject", ""),
                    }
                except Exception as e:
                    logger.error(f"Error loading email templates for {slug}: {e}")
                    channel_previews["email"] = {"error": str(e)}

            elif channel_name == "slack":
                # Load Slack template
                try:
                    slack_template = get_template(f"{template_path}.slack")
                    slack_source = slack_template.template.source

                    channel_previews["slack"] = {
                        "template": slack_source,
                        "format": "json",
                    }
                except Exception as e:
                    logger.error(f"Error loading slack template for {slug}: {e}")
                    channel_previews["slack"] = {"error": str(e)}

            elif channel_name == "sms":
                # Load SMS template
                try:
                    sms_template = get_template(f"{template_path}.sms")
                    sms_source = sms_template.template.source

                    channel_previews["sms"] = {"text": sms_source}
                except Exception as e:
                    logger.error(f"Error loading sms template for {slug}: {e}")
                    channel_previews["sms"] = {"error": str(e)}

        # Get variable metadata
        variables = self.get_available_variables(slug, academy=academy)

        return {
            "slug": notification["slug"],
            "name": notification["name"],
            "description": notification["description"],
            "category": notification["category"],
            "channels": channel_previews,
            "variables": variables,
        }


# Singleton instance
EmailManager = EmailManagerClass()

