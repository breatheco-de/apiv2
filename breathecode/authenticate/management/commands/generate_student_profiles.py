from django.core.management.base import BaseCommand
from breathecode.admissions.models import CohortUser
from ...models import ProfileAcademy, Role


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    def handle(self, *args, **options):

        student_role = Role.objects.get(slug="student")
        cus = CohortUser.objects.filter(role="STUDENT")
        count = 0
        for cu in cus:
            profile = ProfileAcademy.objects.filter(user=cu.user, academy=cu.cohort.academy).first()
            if profile is None:
                count = count + 1
                profile = ProfileAcademy(
                    user=cu.user,
                    academy=cu.cohort.academy,
                    role=student_role,
                    email=cu.user.email,
                    first_name=cu.user.first_name,
                    last_name=cu.user.last_name,
                    status="ACTIVE",
                )
                profile.save()
        print(f"{count} student AcademyProfiles were created")
