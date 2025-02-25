import logging
from django.core.management.base import BaseCommand
from ...models import KeywordCluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "This commands converts the lang of all the keyword clusters to lower case"

    def handle(self, *args, **options):

        keyword_clusters = KeywordCluster.objects.all()
        for elem in keyword_clusters:
            elem.lang = elem.lang.lower()
            elem.save()
