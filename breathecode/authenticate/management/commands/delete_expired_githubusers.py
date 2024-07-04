from django.core.management.base import BaseCommand
from ...models import AcademyAuthSettings, GithubAcademyUser
from breathecode.admissions.models import CohortUser
from breathecode.services.github import Github


class Command(BaseCommand):
    help = "Delete expired temporal and login tokens"

    def handle(self, *args, **options):
        self.update_inactive_github_users()
        self.delete_from_github_org()

    def delete_from_github_org(self):
        academies: dict[str, Github] = {}
        deleted_users = GithubAcademyUser.objects.filter(storage_action="DELETE", storage_status="SYNCHED")
        for github in deleted_users:
            if github.academy.id not in academies:
                settings = AcademyAuthSettings.objects.filter(academy__id=github.academy.id).first()
                academies[github.academy.id] = Github(
                    org=settings.github_username, token=settings.github_owner.credentialsgithub.token
                )

            gb = academies[github.academy.id]

            try:
                gb.delete_org_member(github.username)
                github.log("Successfully deleted in github organization")
                print("Deleted github user: " + github.username)
            except Exception as e:
                github.log("Error calling github API while deleting member from org: " + str(e))
                print("Error deleting github user: " + github.username)

    def is_user_active_in_other_cohorts(self, user, current_cohort, academy):
        active_cohorts_count = (
            CohortUser.objects.filter(
                user=user,
                cohort__academy=academy,
                cohort__never_ends=False,
                educational_status="ACTIVE",
            )
            .exclude(cohort__id__in=[current_cohort.id])
            .count()
        )
        return active_cohorts_count > 0

    def update_inactive_github_users(self):
        added_github_users = GithubAcademyUser.objects.filter(storage_action="ADD")
        print(str(added_github_users.count()) + " users found")
        for github_user in added_github_users:
            user = github_user.user
            academy = github_user.academy

            cohort_user = CohortUser.objects.filter(
                user=user,
                cohort__never_ends=False,
                educational_status__in=["POSTPONED", "SUSPENDED", "GRADUATED", "DROPPED"],
                cohort__academy=academy,
            ).first()

            if cohort_user is None:
                continue

            cohort = cohort_user.cohort
            if not self.is_user_active_in_other_cohorts(user, cohort, academy):
                github_user.storage_action = "DELETE"
                github_user.storage_status = "PENDING"
                github_user.save()
                print(
                    "Schedule the following github user for deletion in Academy "
                    + github_user.academy.name
                    + ". User: "
                    + github_user.user.email
                )
