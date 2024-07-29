from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = "breathecode.assignments"

    def ready(self):
        from . import receivers  # noqa: F401
