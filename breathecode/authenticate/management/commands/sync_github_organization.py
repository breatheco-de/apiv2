from django.core.management.base import BaseCommand

from ...actions import sync_organization_members
from ...models import AcademyAuthSettings, GithubAcademyUser


class Command(BaseCommand):
    help = (
        "Sincroniza miembros de la organización de GitHub con GithubAcademyUser "
        "para cada academia con github_is_sync activo. "
        "Opcionalmente, procesa un solo registro (p. ej. reintentar invitación)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--github-academy-user-id",
            type=int,
            default=None,
            help="Solo este GithubAcademyUser (misma lógica que el sync global, en una fila).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Con --github-academy-user-id: poner storage en PENDING+ADD antes de sincronizar.",
        )

    def handle(self, *args, **options):
        gau_id = options["github_academy_user_id"]
        force = options["force"]

        if gau_id is not None:
            gau = GithubAcademyUser.objects.filter(id=gau_id).select_related("academy").first()
            if gau is None:
                self.stderr.write(self.style.ERROR(f"GithubAcademyUser id={gau_id} not found"))
                return
            aca = AcademyAuthSettings.objects.filter(academy_id=gau.academy_id, github_is_sync=True).first()
            if not aca:
                self.stderr.write(
                    self.style.ERROR(
                        f"Academy id={gau.academy_id} has no AcademyAuthSettings with github_is_sync=True; "
                        "enable it before running sync."
                    )
                )
                return
            self.stdout.write(
                f"Syncing only GithubAcademyUser id={gau_id} (academy {gau.academy_id} — {gau.academy.name})"
            )
            try:
                ok = sync_organization_members(
                    gau.academy_id,
                    github_academy_user_id=gau_id,
                    force_requeue=force,
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
                raise
            if not ok:
                self.stderr.write(self.style.WARNING("sync_organization_members returned False (is sync disabled?)."))
            else:
                self.stdout.write(self.style.SUCCESS("Done."))
            return

        aca_settings = AcademyAuthSettings.objects.filter(github_is_sync=True)
        for settings in aca_settings:
            self.stdout.write(f"Syncing academy {settings.academy.name} organization users")
            try:
                sync_organization_members(settings.academy.id)
            except Exception as e:
                self.stderr.write(f"Error synching members for academy {settings.academy.id}: {e}")
                raise
