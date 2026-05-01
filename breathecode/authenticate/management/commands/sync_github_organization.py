from django.core.management.base import BaseCommand

from ...actions import sync_organization_members
from ...models import AcademyAuthSettings, GithubAcademyUser, INVITE, PENDING, SYNCHED


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
        parser.add_argument(
            "--confirm-sync-invite",
            action="store_true",
            help="Rechequea usuarios SYNCHED+INVITE reencolándolos como PENDING+INVITE antes de sincronizar.",
        )
        parser.add_argument(
            "--academy-id",
            type=int,
            default=None,
            help="Solo esta academia (debe tener github_is_sync activo). Ignorado si usas --github-academy-user-id.",
        )

    def handle(self, *args, **options):
        gau_id = options["github_academy_user_id"]
        force = options["force"]
        confirm_sync_invite = options["confirm_sync_invite"]
        academy_id_filter = options["academy_id"]

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
        if academy_id_filter is not None:
            aca_settings = aca_settings.filter(academy_id=academy_id_filter)
            if not aca_settings.exists():
                self.stderr.write(
                    self.style.ERROR(
                        f"No AcademyAuthSettings with github_is_sync=True for academy_id={academy_id_filter}"
                    )
                )
                return

        for settings in aca_settings:
            self.stdout.write(f"Syncing academy {settings.academy.name} organization users")
            if confirm_sync_invite:
                requeued = GithubAcademyUser.objects.filter(
                    academy=settings.academy,
                    storage_status=SYNCHED,
                    storage_action=INVITE,
                ).update(storage_status=PENDING, storage_synch_at=None)
                self.stdout.write(f"Requeued {requeued} SYNCHED+INVITE users for confirmation")
            try:
                sync_organization_members(settings.academy.id)
            except Exception as e:
                self.stderr.write(f"Error synching members for academy {settings.academy.id}: {e}")
                raise
