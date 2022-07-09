from django.apps import AppConfig


class CommonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'breathecode.commons'

    def ready(self):
        from . import receivers
