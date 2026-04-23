"""
Export academy invites to CSV.

Examples:
    # Todas las invitaciones pendientes (todas las academias)
    python manage.py export_academy_invites_csv

    # Solo una academia
    python manage.py export_academy_invites_csv --academy-id 1 --output pending.csv

    # Otros estados
    python manage.py export_academy_invites_csv --statuses PENDING,REJECTED
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from breathecode.authenticate.models import UserInvite


class Command(BaseCommand):
    help = "Export UserInvite records to CSV (por defecto: todas las PENDING)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy-id",
            type=int,
            default=None,
            help="Si se indica, solo invitaciones de esta academia; si no, todas las academias",
        )
        parser.add_argument(
            "--statuses",
            type=str,
            default="PENDING",
            help="Estados separados por coma (default: PENDING)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Ruta del CSV (default: pending_invites_<ts>.csv o academy_<id>_invites_<ts>.csv)",
        )

    def handle(self, *args, **options):
        academy_id = options["academy_id"]
        raw_statuses = options["statuses"] or ""
        output = options["output"]

        statuses = [x.strip().upper() for x in raw_statuses.split(",") if x.strip()]
        if not statuses:
            raise CommandError("Indica al menos un status en --statuses (ej. PENDING)")

        valid_statuses = {"PENDING", "REJECTED", "WAITING_LIST", "ACCEPTED"}

        invalid_statuses = [x for x in statuses if x not in valid_statuses]
        if invalid_statuses:
            raise CommandError(
                f"Invalid statuses: {', '.join(invalid_statuses)}. "
                f"Valid values are: {', '.join(sorted(valid_statuses))}"
            )

        qs = UserInvite.objects.filter(status__in=statuses).select_related("academy", "role", "user", "author")
        if academy_id is not None:
            qs = qs.filter(academy_id=academy_id)
        qs = qs.order_by("academy_id", "-created_at")

        if output:
            output_path = Path(output).expanduser()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if academy_id is not None:
                output_path = Path(f"academy_{academy_id}_invites_{timestamp}.csv")
            else:
                output_path = Path(f"pending_invites_{timestamp}.csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "invite_id",
                    "academy_id",
                    "academy_name",
                    "email",
                    "first_name",
                    "last_name",
                    "status",
                    "role",
                    "user_id",
                    "author_id",
                    "is_email_validated",
                    "sent_at",
                    "opened_at",
                    "clicked_at",
                    "expires_at",
                    "created_at",
                    "updated_at",
                ]
            )

            for invite in qs:
                writer.writerow(
                    [
                        invite.id,
                        invite.academy_id,
                        invite.academy.name if invite.academy else "",
                        invite.email or "",
                        invite.first_name or "",
                        invite.last_name or "",
                        invite.status,
                        invite.role.slug if invite.role else "",
                        invite.user_id or "",
                        invite.author_id or "",
                        invite.is_email_validated,
                        invite.sent_at.isoformat() if invite.sent_at else "",
                        invite.opened_at.isoformat() if invite.opened_at else "",
                        invite.clicked_at.isoformat() if invite.clicked_at else "",
                        invite.expires_at.isoformat() if invite.expires_at else "",
                        invite.created_at.isoformat() if invite.created_at else "",
                        invite.updated_at.isoformat() if invite.updated_at else "",
                    ]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"CSV generated successfully: {output_path.resolve()} ({qs.count()} rows, statuses={','.join(statuses)})"
            )
        )
