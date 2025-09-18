from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "breathecode.payments"

    def ready(self):
        # always register generic flags
        from . import flags  # noqa: F401

        # register non-team receivers always
        from . import receivers  # noqa: F401

        # conditional wiring for team features
        try:
            from capyc.core.managers import feature
            from .flags import flags as _flags

            if _flags.get("TEAM_MANAGEMENT_ENABLED") in feature.TRUE:
                from . import receivers_team  # noqa: F401

            if _flags.get("TEAM_SUPERVISORS_ENABLED") in feature.TRUE:
                from . import supervisors_team  # noqa: F401
        except Exception:
            # do not fail app boot if feature manager is not available
            pass
