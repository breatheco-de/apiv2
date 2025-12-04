import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

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
        Generate a preview of the notification template.
        
        Returns both the raw source and fully rendered template with placeholder values
        in {VARIABLE_NAME} format, so frontend can display what the email actually looks
        like including parent templates while still seeing variable positions.

        Args:
            slug: The notification slug
            academy: Optional Academy model instance for branding
            channels: Optional list of channels to preview (default: all available)

        Returns:
            dict: Preview data with both source and rendered templates
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

        # Build preview context with schema-driven placeholders
        preview_context = self._build_preview_context(notification, academy)

        # Build preview for each channel
        channel_previews = {}

        for channel_name, channel_config in channels_to_preview.items():
            template_path = channel_config.get("template_path")

            if channel_name == "email":
                try:
                    html_template = get_template(f"{template_path}.html")
                    
                    try:
                        txt_template = get_template(f"{template_path}.txt")
                    except Exception:
                        txt_template = None

                    # Get raw source (child template only)
                    html_source = html_template.template.source
                    txt_source = txt_template.template.source if txt_template else None
                    
                    # Render complete template (includes parent templates with placeholders)
                    html_rendered = html_template.render(preview_context)
                    txt_rendered = txt_template.render(preview_context) if txt_template else None

                    channel_previews["email"] = {
                        "html_source": html_source,          # Raw child template
                        "html_rendered": html_rendered,      # Full rendered HTML
                        "text_source": txt_source,           # Raw text template
                        "text_rendered": txt_rendered,       # Full rendered text
                        "subject": channel_config.get("default_subject", ""),
                    }
                except Exception as e:
                    logger.error(f"Error loading email templates for {slug}: {e}")
                    channel_previews["email"] = {"error": str(e)}

            elif channel_name == "slack":
                try:
                    slack_template = get_template(f"{template_path}.slack")
                    slack_source = slack_template.template.source
                    
                    # Render Slack template with placeholders
                    slack_rendered = slack_template.render(preview_context)

                    channel_previews["slack"] = {
                        "source": slack_source,
                        "rendered": slack_rendered,
                        "format": "json",
                    }
                except Exception as e:
                    logger.error(f"Error loading slack template for {slug}: {e}")
                    channel_previews["slack"] = {"error": str(e)}

            elif channel_name == "sms":
                try:
                    sms_template = get_template(f"{template_path}.sms")
                    sms_source = sms_template.template.source
                    
                    # Render SMS template with placeholders
                    sms_rendered = sms_template.render(preview_context)

                    channel_previews["sms"] = {
                        "source": sms_source,
                        "rendered": sms_rendered,
                    }
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
            "preview_context": preview_context,  # Show what values were used for preview
        }

    def _build_preview_context(self, notification: dict, academy=None) -> dict:
        """
        Build context with variable name placeholders using registry schema.
        Intelligently parses schema to create proper placeholder structures.
        Variables are replaced with {VARIABLE_NAME} format so frontend can see
        the complete rendered template structure while still identifying variables.
        
        Args:
            notification: Notification configuration dict from registry
            academy: Optional Academy instance for branding
        
        Returns:
            dict: Context with variables as {VARIABLE_NAME} placeholders
        """
        # Start with default variables - use actual values for these
        context = {
            "API_URL": os.environ.get("API_URL", "https://api.4geeks.com"),
            "COMPANY_NAME": os.environ.get("COMPANY_NAME", "4Geeks"),
            "COMPANY_CONTACT_URL": os.environ.get("COMPANY_CONTACT_URL", "https://4geeks.com/contact"),
            "COMPANY_LEGAL_NAME": os.environ.get("COMPANY_LEGAL_NAME", "4Geeks LLC"),
            "COMPANY_ADDRESS": os.environ.get("COMPANY_ADDRESS", ""),
            "COMPANY_INFO_EMAIL": os.environ.get("COMPANY_INFO_EMAIL", "info@4geeks.com"),
            "COMPANY_LOGO": "https://storage.googleapis.com/breathecode/logos/4geeks-vertical-logo.png",
            "style__success": "#99ccff",
            "style__danger": "#ffcccc",
            "style__secondary": "#ededed",
        }
        
        # Override with academy-specific values if provided
        if academy:
            context.update({
                "COMPANY_INFO_EMAIL": academy.feedback_email if hasattr(academy, "feedback_email") else context["COMPANY_INFO_EMAIL"],
                "COMPANY_LEGAL_NAME": academy.legal_name or academy.name if hasattr(academy, "legal_name") else academy.name,
                "COMPANY_LOGO": academy.logo_url if hasattr(academy, "logo_url") else context["COMPANY_LOGO"],
                "COMPANY_NAME": academy.name if hasattr(academy, "name") else context["COMPANY_NAME"],
            })
        
        # Process each variable from the registry schema
        for var in notification.get("variables", []):
            var_name = var["name"]
            context[var_name] = self._create_placeholder_from_schema(var)
        
        # Add common context variables as placeholders
        context.setdefault("subject", "{subject}")
        context.setdefault("SUBJECT", "{SUBJECT}")
        
        return context

    def _create_placeholder_from_schema(self, var: dict) -> Any:
        """
        Create placeholder value from registry variable schema.
        Uses example, description, and source fields to determine structure.
        
        Args:
            var: Variable definition from registry with name, description, source, example
        
        Returns:
            Placeholder value matching the variable structure
        """
        var_name = var["name"]
        example = var.get("example", "")
        description = var.get("description", "").lower()
        source = var.get("source", "").lower()
        
        # Strategy 1: Try to parse example as JSON
        if example:
            try:
                parsed_example = json.loads(example)
                # If it's a dict/object, convert values to placeholders
                if isinstance(parsed_example, dict):
                    return self._dict_to_placeholders(parsed_example, var_name)
                # If it's a list/array, convert items to placeholders
                elif isinstance(parsed_example, list):
                    return self._list_to_placeholders(parsed_example, var_name)
            except (json.JSONDecodeError, TypeError):
                # Not valid JSON, try other strategies
                pass
        
        # Strategy 2: Check description for structure hints
        if "list" in description or "array" in description:
            # It's an array - create a single-item placeholder array
            return self._infer_array_structure(var, var_name)
        
        if "object" in description or "." in description:
            # It's an object - extract properties from description
            return self._infer_object_structure(var, var_name, description)
        
        # Strategy 3: Check source for serializer hints
        if "serializer" in source:
            # It's a serialized object - infer structure from serializer name
            return self._infer_from_serializer(var_name, source)
        
        # Strategy 4: Default - simple string placeholder
        return f"{{{var_name}}}"

    def _dict_to_placeholders(self, obj: dict, var_name: str) -> dict:
        """Convert dict example to placeholder dict with {var.key} format."""
        result = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                result[key] = self._dict_to_placeholders(value, f"{var_name}.{key}")
            elif isinstance(value, list):
                result[key] = self._list_to_placeholders(value, f"{var_name}.{key}")
            else:
                result[key] = f"{{{var_name}.{key}}}"
        return result

    def _list_to_placeholders(self, arr: list, var_name: str) -> list:
        """Convert list example to placeholder list with {var[index].key} format."""
        if not arr:
            return [f"{{{var_name}[0]}}"]
        
        # Use first item as template
        first_item = arr[0]
        if isinstance(first_item, dict):
            placeholder_item = self._dict_to_placeholders(first_item, f"{var_name}[0]")
        elif isinstance(first_item, list):
            placeholder_item = self._list_to_placeholders(first_item, f"{var_name}[0]")
        else:
            placeholder_item = f"{{{var_name}[0]}}"
        
        return [placeholder_item]

    def _infer_array_structure(self, var: dict, var_name: str) -> list:
        """Infer array structure from description or example."""
        example = var.get("example", "")
        
        # Try to extract structure from example string (even if not valid JSON)
        # e.g., "[{academy: {name: 'Miami Academy'}, role: 'STUDENT'}]"
        if "{" in example and "}" in example:
            # Looks like array of objects
            # Extract property names from example
            props = re.findall(r'(\w+):', example)
            if props:
                placeholder_obj = {}
                for prop in props:
                    if prop == 'academy':
                        # Handle nested objects mentioned in example
                        placeholder_obj['academy'] = {'name': f"{{{var_name}[0].academy.name}}"}
                    else:
                        placeholder_obj[prop] = f"{{{var_name}[0].{prop}}}"
                return [placeholder_obj]
        
        return [f"{{{var_name}[0]}}"]

    def _infer_object_structure(self, var: dict, var_name: str, description: str) -> dict:
        """Infer object structure from description mentioning properties."""
        # Extract property references like "user.first_name" from description
        property_pattern = r'(\w+)\.(\w+)'
        matches = re.findall(property_pattern, description)
        
        if matches:
            # Group by parent object
            structure = {}
            for parent, prop in matches:
                if parent == var_name or len(matches) == 1:
                    # Direct property
                    structure[prop] = f"{{{var_name}.{prop}}}"
                else:
                    # Nested object
                    if parent not in structure:
                        structure[parent] = {}
                    if isinstance(structure[parent], dict):
                        structure[parent][prop] = f"{{{var_name}.{parent}.{prop}}}"
            
            if structure:
                return structure
        
        # Fallback: create basic structure
        return {"property": f"{{{var_name}.property}}"}

    def _infer_from_serializer(self, var_name: str, source: str) -> dict:
        """Infer object structure from serializer name in source."""
        # Common serializer patterns
        if "usersmallserializer" in source or "userserializer" in source:
            return {
                "id": f"{{{var_name}.id}}",
                "first_name": f"{{{var_name}.first_name}}",
                "last_name": f"{{{var_name}.last_name}}",
                "email": f"{{{var_name}.email}}",
            }
        
        if "academysmallserializer" in source or "academyserializer" in source:
            return {
                "id": f"{{{var_name}.id}}",
                "name": f"{{{var_name}.name}}",
                "slug": f"{{{var_name}.slug}}",
            }
        
        # Generic object placeholder
        return {"property": f"{{{var_name}.property}}"}


# Singleton instance
EmailManager = EmailManagerClass()

