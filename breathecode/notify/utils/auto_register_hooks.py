"""
Auto-register webhook receivers based on HOOK_EVENTS_METADATA configuration.

This module dynamically creates signal receivers for webhook events based on the
metadata defined in settings.HOOK_EVENTS_METADATA. This eliminates the need to
manually write boilerplate receiver functions for standard webhook events.

Events that include 'signal', 'sender', and 'event_action' in their metadata
will automatically get receivers registered (unless auto_register=False).

Example HOOK_EVENTS_METADATA entry that will auto-register:
    "assignment.assignment_created": {
        "action": "assignments.Task.assignment_created",
        "category": "assignments",
        "description": "Triggered when a new assignment is created",
        "model": "assignments.Task",
        "signal": "breathecode.assignments.signals.assignment_created",
        "sender": "breathecode.assignments.models.Task",
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
        "event_action": "assignment_created",
    }
"""

import logging
from importlib import import_module

from django.conf import settings

logger = logging.getLogger(__name__)


def import_from_string(import_path):
    """
    Import a class or function from a string path.

    Args:
        import_path: String like 'breathecode.assignments.models.Task'

    Returns:
        The imported object
    """
    if not import_path:
        return None

    try:
        module_path, class_name = import_path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, AttributeError, ImportError) as e:
        logger.error(f"Failed to import {import_path}: {e}")
        return None


def derive_signal_from_action(action):
    """
    Derive signal import path from action string.

    Args:
        action: Action string like 'admissions.CohortUser.edu_status_updated'

    Returns:
        Signal import path like 'breathecode.admissions.signals.edu_status_updated'
        or None if cannot be derived

    Examples:
        'admissions.CohortUser.edu_status_updated'
            -> 'breathecode.admissions.signals.edu_status_updated'
        'assignments.Task.assignment_created'
            -> 'breathecode.assignments.signals.assignment_created'
    """
    try:
        parts = action.split(".")
        if len(parts) < 3:
            return None

        app_name = parts[0]  # e.g., 'admissions'
        # model_name = parts[1]  # e.g., 'CohortUser'
        signal_name = parts[2]  # e.g., 'edu_status_updated'

        return f"breathecode.{app_name}.signals.{signal_name}"
    except Exception as e:
        logger.debug(f"Could not derive signal from action '{action}': {e}")
        return None


def derive_sender_from_action(action):
    """
    Derive sender model import path from action string.

    Args:
        action: Action string like 'admissions.CohortUser.edu_status_updated'

    Returns:
        Sender import path like 'breathecode.admissions.models.CohortUser'
        or None if cannot be derived

    Examples:
        'admissions.CohortUser.edu_status_updated'
            -> 'breathecode.admissions.models.CohortUser'
        'assignments.Task.assignment_created'
            -> 'breathecode.assignments.models.Task'
    """
    try:
        parts = action.split(".")
        if len(parts) < 3:
            return None

        app_name = parts[0]  # e.g., 'admissions'
        model_name = parts[1]  # e.g., 'CohortUser'

        return f"breathecode.{app_name}.models.{model_name}"
    except Exception as e:
        logger.debug(f"Could not derive sender from action '{action}': {e}")
        return None


def derive_event_action_from_action(action):
    """
    Derive event action name from action string.

    Args:
        action: Action string like 'admissions.CohortUser.edu_status_updated'

    Returns:
        Event action name like 'edu_status_updated'
        or None if cannot be derived

    Examples:
        'admissions.CohortUser.edu_status_updated' -> 'edu_status_updated'
        'assignments.Task.assignment_created' -> 'assignment_created'
        'marketing.FormEntry.created+' -> None (special action, not custom)
    """
    try:
        parts = action.split(".")
        if len(parts) < 3:
            return None

        event_action = parts[2]  # e.g., 'edu_status_updated'

        # Don't auto-derive for special actions (created+, updated+, deleted+)
        if event_action.endswith("+"):
            return None

        return event_action
    except Exception as e:
        logger.debug(f"Could not derive event_action from action '{action}': {e}")
        return None


def derive_app_from_action(action):
    """
    Derive app name from action string.

    Args:
        action: Action string like 'admissions.CohortUser.edu_status_updated'

    Returns:
        App name like 'admissions'
        or None if cannot be derived

    Examples:
        'admissions.CohortUser.edu_status_updated' -> 'admissions'
        'assignments.Task.assignment_created' -> 'assignments'
        'marketing.FormEntry.created+' -> 'marketing'
    """
    try:
        parts = action.split(".")
        if len(parts) < 1:
            return None

        return parts[0]  # e.g., 'admissions'
    except Exception as e:
        logger.debug(f"Could not derive app from action '{action}': {e}")
        return None


def derive_model_from_action(action):
    """
    Derive model label from action string.

    Args:
        action: Action string like 'admissions.CohortUser.edu_status_updated'

    Returns:
        Model label like 'admissions.CohortUser'
        or None if cannot be derived

    Examples:
        'admissions.CohortUser.edu_status_updated' -> 'admissions.CohortUser'
        'assignments.Task.assignment_created' -> 'assignments.Task'
        'marketing.FormEntry.created+' -> 'marketing.FormEntry'
    """
    try:
        parts = action.split(".")
        if len(parts) < 2:
            return None

        # Return app.Model
        return f"{parts[0]}.{parts[1]}"  # e.g., 'admissions.CohortUser'
    except Exception as e:
        logger.debug(f"Could not derive model from action '{action}': {e}")
        return None


def derive_label_from_action(action):
    """
    Derive human-readable label from action string by de-slugifying the last part.

    Args:
        action: Action string like 'assignments.Task.assignment_created'

    Returns:
        Human-readable label like 'Assignment Created'
        or None if cannot be derived

    Examples:
        'assignments.Task.assignment_created' -> 'Assignment Created'
        'admissions.CohortUser.edu_status_updated' -> 'Edu Status Updated'
        'marketing.FormEntry.created+' -> 'Created'
        'event.Event.event_rescheduled' -> 'Event Rescheduled'
    """
    try:
        parts = action.split(".")
        if len(parts) < 3:
            return None

        # Get the last part (e.g., 'assignment_created' or 'created+')
        last_part = parts[2]

        # Remove the '+' suffix if present
        last_part = last_part.rstrip("+")

        # Convert snake_case to Title Case
        # 'assignment_created' -> 'Assignment Created'
        words = last_part.split("_")
        label = " ".join(word.capitalize() for word in words)

        return label
    except Exception as e:
        logger.debug(f"Could not derive label from action '{action}': {e}")
        return None


def get_model_label(instance):
    """Get the model label for an instance."""
    if instance is None:
        return None
    opts = instance._meta.concrete_model._meta
    try:
        return opts.label
    except AttributeError:
        return ".".join([opts.app_label, opts.object_name])


def create_hook_receiver(event_name, event_config):
    """
    Create a dynamic receiver function for a webhook event.

    Args:
        event_name: The webhook event name (e.g., 'assignment.assignment_created')
        event_config: The configuration dict from HOOK_EVENTS_METADATA

    Returns:
        A receiver function
    """
    from breathecode.notify.utils.hook_manager import HookManager

    serializer_class = import_from_string(event_config.get("serializer"))
    event_action = event_config.get("event_action")

    def hook_receiver(sender, instance, **kwargs):
        """Auto-generated webhook receiver."""
        logger.debug(f"HOOK: {event_name} triggered")

        model_label = get_model_label(instance)

        # Serialize payload if serializer is provided
        payload_override = None
        if serializer_class:
            try:
                serializer = serializer_class(instance)
                payload_override = serializer.data
            except Exception as e:
                logger.error(f"Failed to serialize {event_name}: {e}")

        # Determine academy override if available
        academy_override = None
        if hasattr(instance, "academy"):
            academy_override = instance.academy

        # Process the hook event
        HookManager.process_model_event(
            instance, model_label, event_action, payload_override=payload_override, academy_override=academy_override
        )

    # Set a meaningful name for debugging
    hook_receiver.__name__ = f"auto_{event_name.replace('.', '_')}_receiver"

    return hook_receiver


def auto_register_webhook_receivers():
    """
    Automatically register webhook receivers based on HOOK_EVENTS_METADATA.

    This function should be called once when the Django app initializes
    (typically in the notify app's ready() method).

    Signal and sender paths can be:
    - Explicitly provided in metadata
    - Auto-derived from the action string (e.g., 'app.Model.signal_name')

    Events with auto_register=False are skipped.
    Events without event_action are skipped (likely using post_save/post_delete).
    """
    metadata = getattr(settings, "HOOK_EVENTS_METADATA", {})
    registered_count = 0
    skipped_count = 0
    derived_count = 0

    for event_name, config in metadata.items():
        # Skip if auto_register is explicitly False
        if config.get("auto_register") is False:
            logger.debug(f"Skipping auto-registration for {event_name} (auto_register=False)")
            skipped_count += 1
            continue

        # Get or derive event_action
        event_action = config.get("event_action")
        if not event_action:
            # Try to derive from action
            action = config.get("action")
            if action:
                event_action = derive_event_action_from_action(action)
                if event_action:
                    logger.debug(f"Derived event_action for {event_name}: {event_action}")
                    derived_count += 1
                    # Store derived event_action in config so create_hook_receiver can use it
                    config["event_action"] = event_action

        # event_action is required for auto-registration
        if not event_action:
            # This is normal for events that use post_save/post_delete (created+, updated+, deleted+)
            continue

        # Get or derive signal path
        signal_path = config.get("signal")
        if not signal_path:
            # Try to derive from action
            action = config.get("action")
            if action:
                signal_path = derive_signal_from_action(action)
                if signal_path:
                    logger.debug(f"Derived signal path for {event_name}: {signal_path}")
                    derived_count += 1

        # Get or derive sender path
        sender_path = config.get("sender")
        if not sender_path:
            # Try to derive from action
            action = config.get("action")
            if action:
                sender_path = derive_sender_from_action(action)
                if sender_path:
                    logger.debug(f"Derived sender path for {event_name}: {sender_path}")

        # Both signal and sender are required
        if not signal_path or not sender_path:
            logger.debug(
                f"Skipping {event_name}: Missing signal or sender "
                f"(signal={bool(signal_path)}, sender={bool(sender_path)})"
            )
            continue

        # Import signal and sender
        signal_obj = import_from_string(signal_path)
        sender_model = import_from_string(sender_path)

        if signal_obj is None or sender_model is None:
            logger.warning(
                f"Failed to auto-register {event_name}: Could not import "
                f"signal ({signal_path}) or sender ({sender_path})"
            )
            skipped_count += 1
            continue

        # Create and register the receiver
        receiver_func = create_hook_receiver(event_name, config)

        # Register with Django's receiver decorator
        signal_obj.connect(receiver_func, sender=sender_model)

        logger.debug(f"Auto-registered receiver for {event_name}")
        registered_count += 1

    logger.info(
        f"Auto-registered {registered_count} webhook receivers "
        f"({derived_count} with derived paths), skipped {skipped_count}"
    )
