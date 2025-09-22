from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "breathecode.payments"

    def ready(self):
        # always register generic flags
        from . import flags  # noqa: F401

        # register non-team receivers always
        from . import receivers  # noqa: F401
        from . import supervisors  # noqa: F401
