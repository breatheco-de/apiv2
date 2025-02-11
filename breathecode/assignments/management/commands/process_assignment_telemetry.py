from django.core.management.base import BaseCommand
from breathecode.assignments.models import LearnPackWebhook
from breathecode.assignments.tasks import async_learnpack_webhook


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def handle(self, *args, **options):
        pending_webhooks = LearnPackWebhook.objects.filter(status="PENDING").order_by("created_at")
        processed_webhooks = {}

        for webhook in pending_webhooks:
            key = (webhook.payload.get("user_id"), webhook.payload.get("asset_id") or webhook.payload.get("slug"))
            if key not in processed_webhooks:
                self.stdout.write(self.style.NOTICE(f"Enqueued telemetry for user,asset: {str(key)}"))
                async_learnpack_webhook.delay(webhook.id)
                processed_webhooks[key] = webhook.id
            else:
                self.stdout.write(self.style.NOTICE(f"Ignored telemetry for user,asset: {str(key)}"))
                webhook.status = "IGNORED"
                webhook.status_text = "Ignored because a more recent telemetry batch was obtained."
                webhook.save()
