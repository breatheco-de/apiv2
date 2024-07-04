from django.core.management.base import BaseCommand
from ...models import EventbriteWebhook
import breathecode.events.tasks as tasks


class Command(BaseCommand):
    help = "Sync all the EventbriteWebhook of type order.placed"

    def handle(self, *args, **options):
        for element in EventbriteWebhook.objects.filter(action="order.placed"):
            tasks.async_eventbrite_webhook.delay(element.id)
