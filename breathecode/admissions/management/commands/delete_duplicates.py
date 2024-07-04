import os
from django.core.management.base import BaseCommand
from ...models import CohortUser

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = "Delete duplicate cohort users imported from old breathecode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        # acc
        result = []

        # collector
        qs = CohortUser.objects.order_by("id")
        for user_id, cohort_id in set(qs.values_list("user__id", "cohort__id")):
            result.append(
                qs.filter(user__id=user_id, cohort__id=cohort_id).values("id", "user__id", "cohort__id").first()
            )

        # remove dups
        for data in result:
            id = data["id"]
            user = data["user__id"]
            cohort = data["cohort__id"]

            # # first graduated students
            # pref = CohortUser.objects.filter(user__id=user, cohort__id=cohort,
            #     educational_status='GRADUATED').first()

            # # second students with a educational_status and finantial_status
            # if pref is None:
            #     pref = (CohortUser.objects.filter(user__id=data['user__id'],
            #         cohort__id=data['cohort__id']).exclude(educational_status=None,
            #         finantial_status=None)).first()

            # # third students with a educational_status
            # if pref is None:
            #     pref = (CohortUser.objects.filter(user__id=data['user__id'],
            #         cohort__id=data['cohort__id']).exclude(educational_status=None)).first()

            # # fourth students with a finantial_status
            # if pref is None:
            #     pref = (CohortUser.objects.filter(user__id=data['user__id'],
            #         cohort__id=data['cohort__id']).exclude(finantial_status=None)).first()

            # # if some is match, set id of element that cannot be delete
            # if pref:
            #     id = pref.id

            # bulk delete but cohort user with that id
            (CohortUser.objects.filter(user__id=user, cohort__id=cohort).exclude(id=id).delete())

        self.stdout.write(self.style.SUCCESS("Remove duplicates from cohort users has ended"))
