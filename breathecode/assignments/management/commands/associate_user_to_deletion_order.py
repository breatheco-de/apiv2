from django.core.management.base import BaseCommand

from breathecode.assignments.models import RepositoryDeletionOrder, Task


class Command(BaseCommand):
    help = "Relate Repository Deletion Orders to Users"

    def handle(self, *args, **options):
        deletion_orders = RepositoryDeletionOrder.objects.filter(user__isnull=True)
        for deletion_order in deletion_orders:
            task = Task.objects.filter(github_url__icontains=deletion_order.repository_user).first()
            if task is not None:
                deletion_order.user = task.user
                deletion_order.save()
