from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import Event, EventbriteWebhook, FINISHED


class Command(BaseCommand):
    help = "Delete logs and other garbage"

    def end_past_events(self):
        """Mark ACTIVE events whose ending_at has passed as FINISHED and set ended_at."""
        utc_now = timezone.now()
        events_to_end = Event.objects.filter(
            status="ACTIVE",
            ended_at__isnull=True,
            ending_at__lt=utc_now,
        )
        count_ended = 0
        for event in events_to_end:
            event.ended_at = event.ending_at
            event.status = FINISHED
            event.save()
            count_ended += 1
            self.stdout.write(self.style.NOTICE(f"Ended event {event.id} ({event.title})"))
        if count_ended:
            self.stdout.write(
                self.style.SUCCESS(f"Marked {count_ended} event(s) as FINISHED with ended_at set.")
            )

    def delete_old_webhooks(self):
        """Delete old EventbriteWebhook records (done after 30 days, errored after 60 days)."""
        utc_now = timezone.now()
        how_many_days_with_error = 60
        how_many_days_with_done = 30

        webhooks = EventbriteWebhook.objects.filter(
            created_at__lte=utc_now - timedelta(days=how_many_days_with_done), status="DONE"
        )
        count_done = webhooks.count()
        webhooks.delete()

        webhooks = EventbriteWebhook.objects.filter(
            created_at__lte=utc_now - timedelta(days=how_many_days_with_error)
        ).exclude(status="DONE")
        count_error = webhooks.count()
        webhooks.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {str(count_done)} done, and {str(count_error)} errored EventbriteWebhook's"
            )
        )

    def handle(self, *args, **options):
        self.end_past_events()
        self.delete_old_webhooks()
