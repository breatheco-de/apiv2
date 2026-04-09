import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RegistryConfig(AppConfig):
    name = "breathecode.provisioning"

    def ready(self):
        logger.debug("Loading provisioning.receivers")
        from . import actions  # noqa: F401
        from . import receivers  # noqa: F401
        from . import supervisors  # noqa: F401

        try:
            import breathecode.services.hostinger.client  # noqa: F401 - register Hostinger VPS client
        except ImportError:
            pass

        try:
            import breathecode.services.litellm.client  # noqa: F401
        except ImportError:
            pass

        try:
            import breathecode.services.digitalocean.client  # noqa: F401 - register DigitalOcean VPS client
        except ImportError:
            pass
