from django.apps import AppConfig


class NotifyConfig(AppConfig):
    name = "breathecode.notify"

    def ready(self):
        from . import receivers  # noqa: F401
        
        # Auto-register webhook receivers based on HOOK_EVENTS_METADATA
        from .utils.auto_register_hooks import auto_register_webhook_receivers
        
        auto_register_webhook_receivers()