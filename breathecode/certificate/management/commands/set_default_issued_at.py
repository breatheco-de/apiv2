from django.core.management.base import BaseCommand
import breathecode.certificate.actions as actions


class Command(BaseCommand):
    help = "sets default issued_at for new certificates"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):

        actions.certificate_set_default_issued_at()
