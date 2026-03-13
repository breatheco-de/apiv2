from django.core.management.base import BaseCommand
from breathecode.authenticate.models import ProfileAcademy
from breathecode.admissions.models import Academy
from breathecode.payments.models import PlanFinancing, Subscription


class Command(BaseCommand):
    help = "Checks for users in the academy without any active plans (subscriptions or plan financings). Shows results in console."

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy-slug",
            type=str,
            help="Academy slug to check",
        )
        parser.add_argument(
            "--academy-id",
            type=int,
            help="Academy ID to check",
        )

    def handle(self, *args, **options):
        # Obtener la academia
        academy = None

        if options.get("academy_slug"):
            academy = Academy.objects.filter(slug=options["academy_slug"]).first()
            if not academy:
                self.stdout.write(
                    self.style.ERROR(f"Academia con slug '{options['academy_slug']}' no encontrada")
                )
                return
        elif options.get("academy_id"):
            academy = Academy.objects.filter(id=options["academy_id"]).first()
            if not academy:
                self.stdout.write(
                    self.style.ERROR(f"Academia con ID '{options['academy_id']}' no encontrada")
                )
                return
        else:
            self.stdout.write(self.style.ERROR("Debes proporcionar --academy-slug o --academy-id"))
            return

        # Get all active users in the academy
        active_users = ProfileAcademy.objects.filter(
            academy__id=academy.id,
            status="ACTIVE",
            user__isnull=False,
        ).select_related("user", "role")

        users_without_plans = []

        for profile_academy in active_users:
            user = profile_academy.user

            # Check if user has any subscriptions
            has_subscription = Subscription.objects.filter(user=user).exists()

            # Check if user has any plan financing
            has_plan_financing = PlanFinancing.objects.filter(user=user).exists()

            # If user has neither, they don't have a plan
            if not has_subscription and not has_plan_financing:
                users_without_plans.append(
                    {
                        "user": user,
                        "profile_academy": profile_academy,
                    }
                )

        # Mostrar resultados en consola
        self.stdout.write(f"\nAcademia: {academy.name} (slug: {academy.slug}, id: {academy.id})")

        if len(users_without_plans) > 0:
            self.stdout.write(f"\n{'='*80}")
            self.stdout.write(
                self.style.WARNING(f"Se encontraron {len(users_without_plans)} usuarios sin planes:")
            )
            self.stdout.write(f"{'='*80}\n")

            for idx, user_info in enumerate(users_without_plans, 1):
                user = user_info["user"]
                profile_academy = user_info["profile_academy"]

                self.stdout.write(f"{idx}. {user.first_name} {user.last_name} ({user.email})")
                self.stdout.write(f"   - User ID: {user.id}")
                self.stdout.write(f"   - ProfileAcademy ID: {profile_academy.id}")
                self.stdout.write(
                    f"   - Role: {profile_academy.role.slug if profile_academy.role else 'N/A'}"
                )
                self.stdout.write("")

            self.stdout.write(f"{'='*80}")
            self.stdout.write(
                self.style.WARNING(f"Total: {len(users_without_plans)} usuarios sin planes")
            )
            self.stdout.write(f"{'='*80}\n")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Todos los usuarios activos tienen planes ({active_users.count()} usuarios verificados)\n"
                )
            )
