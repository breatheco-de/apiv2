from django.core.management.base import BaseCommand
from breathecode.assignments.models import AssignmentTelemetry
from breathecode.registry.models import Asset


class Command(BaseCommand):
    help = "Update assets slugs in assignments telemetry"

    def handle(self, *args, **options):
        try:
            telemetries = AssignmentTelemetry.objects.all()
            for assignment_telemetry in telemetries:
                asset_slug = assignment_telemetry.asset_slug
                asset = Asset.get_by_slug(asset_slug)
                if asset is not None and asset.slug != asset_slug:
                    assignment_telemetry.asset_slug = asset.slug
                    assignment_telemetry.save()
        except Exception:
            self.stderr.write("Failed to update telemetry assets slugs")
