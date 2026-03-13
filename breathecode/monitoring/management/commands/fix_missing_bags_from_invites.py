from django.core.management.base import BaseCommand
from django.utils import timezone
from breathecode.authenticate.models import ProfileAcademy, UserInvite
from breathecode.admissions.models import Academy, CohortUser
from breathecode.payments.models import (
    Bag,
    Invoice,
    Plan,
    PlanFinancing,
    Subscription,
    ProofOfPayment,
)
from breathecode.payments import tasks as payments_tasks


class Command(BaseCommand):
    help = "Crea retroactivamente los Bags faltantes para usuarios que aceptaron invitaciones pero no tienen Bag."

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy-slug",
            type=str,
            help="Academy slug to fix",
        )
        parser.add_argument(
            "--academy-id",
            type=int,
            help="Academy ID to fix",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Process only a specific user by email",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating it",
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

        dry_run = options.get("dry_run", False)

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"Arreglando Bags faltantes en: {academy.name} (slug: {academy.slug})")
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: No se crearán Bags"))
        self.stdout.write(f"{'='*80}\n")

        # Get all active users in the academy without plans
        active_users = ProfileAcademy.objects.filter(
            academy__id=academy.id,
            status="ACTIVE",
            user__isnull=False,
        ).select_related("user", "role")

        users_without_plans = []
        for profile_academy in active_users:
            user = profile_academy.user

            # Filtrar por email específico si se proporciona
            if options.get("user_email") and user.email != options["user_email"]:
                continue

            # Check if user has any subscriptions or plan financings
            has_subscription = Subscription.objects.filter(user=user).exists()
            has_plan_financing = PlanFinancing.objects.filter(user=user).exists()

            if not has_subscription and not has_plan_financing:
                users_without_plans.append(
                    {
                        "user": user,
                        "profile_academy": profile_academy,
                    }
                )

        self.stdout.write(f"Encontrados {len(users_without_plans)} usuarios sin planes\n")

        fixed_count = 0
        skipped_count = 0
        error_count = 0
        users_with_plans_created = []  # Lista para almacenar usuarios a los que se creó el plan

        for idx, user_info in enumerate(users_without_plans, 1):
            user = user_info["user"]
            profile_academy = user_info["profile_academy"]

            self.stdout.write(f"{idx}. {user.first_name} {user.last_name} ({user.email})")

            # Buscar invitaciones aceptadas con cohort
            accepted_invites = UserInvite.objects.filter(
                email=user.email, status="ACCEPTED", academy=academy, cohort__isnull=False
            ).select_related("cohort", "role", "user", "author", "payment_method")

            if not accepted_invites.exists():
                self.stdout.write(
                    self.style.WARNING("   ⚠️  No se encontraron invitaciones aceptadas con cohort")
                )
                skipped_count += 1
                continue

            for invite in accepted_invites:
                cohort = invite.cohort

                # Verificar condiciones para crear Bag
                # Primero intentar encontrar Plan vinculado al cohort Y a la invitación
                plan = Plan.objects.filter(cohort_set__cohorts=cohort, invites=invite).first()

                # Si no existe, buscar cualquier Plan que tenga el cohort (más flexible)
                if not plan:
                    plan = Plan.objects.filter(cohort_set__cohorts=cohort).first()
                    if plan:
                        self.stdout.write(
                            self.style.WARNING(
                                f"   ⚠️  Plan encontrado para cohort '{cohort.slug}' pero no vinculado a la invitación. "
                                f"Usando Plan: {plan.title or plan.slug}"
                            )
                        )

                if not plan:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   ⚠️  No existe Plan vinculado al cohort '{cohort.slug}'"
                        )
                    )
                    skipped_count += 1
                    continue

                # Verificar si ya existe un Bag para este usuario e invitación
                existing_bag = Bag.objects.filter(
                    user=user, type="INVITED", academy=academy, plans=plan
                ).first()

                if existing_bag:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Ya existe un Bag (ID: {existing_bag.id}) para este usuario y plan")
                    )
                    skipped_count += 1
                    continue

                # Verificar condiciones
                invite_user = invite.user or user

                if not invite_user:
                    self.stdout.write(self.style.ERROR("   ❌ No se puede determinar el usuario"))
                    error_count += 1
                    continue

                if not cohort.academy.main_currency:
                    self.stdout.write(
                        self.style.ERROR("   ❌ cohort.academy.main_currency no está configurado")
                    )
                    error_count += 1
                    continue

                cohort_saas = cohort.available_as_saas
                academy_saas = cohort.academy.available_as_saas
                saas_condition_met = (
                    cohort_saas is True or (cohort_saas is None and academy_saas is True)
                )

                if not saas_condition_met:
                    self.stdout.write(
                        self.style.ERROR(
                            f"   ❌ available_as_saas no está habilitado (cohort: {cohort_saas}, academy: {academy_saas})"
                        )
                    )
                    error_count += 1
                    continue

                # Todas las condiciones se cumplen, crear el Bag
                plan_name = plan.title or plan.slug or f"Plan ID {plan.id}"
                self.stdout.write(f"   ✅ Creando Bag para plan: {plan_name}")

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            "   [DRY-RUN] Se crearía Bag, Invoice y se ejecutaría build_plan_financing"
                        )
                    )
                    fixed_count += 1
                    users_with_plans_created.append(
                        {
                            "user": user,
                            "plan": plan_name,
                            "cohort": cohort.name if cohort else None,
                        }
                    )
                    continue

                try:
                    utc_now = timezone.now()

                    # Crear Bag
                    bag = Bag()
                    bag.chosen_period = "NO_SET"
                    bag.status = "PAID"
                    bag.type = "INVITED"
                    bag.how_many_installments = 1
                    bag.academy = cohort.academy
                    bag.user = invite_user
                    bag.is_recurrent = False
                    bag.was_delivered = False
                    bag.token = None
                    bag.currency = cohort.academy.main_currency
                    bag.expires_at = None
                    
                    # Intentar guardar el Bag, si falla por Redis/Celery, usar bulk_create para evitar signals
                    try:
                        bag.save()
                    except Exception as celery_error:
                        # Si falla por Redis/Celery, guardar directamente en la BD sin signals
                        error_str = str(celery_error).lower()
                        if (
                            "redis" in error_str
                            or "celery" in error_str
                            or "6379" in error_str
                            or "connection" in error_str
                            or "operationalerror" in error_str
                        ):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"   ⚠️  Redis/Celery no disponible, guardando Bag directamente en BD..."
                                )
                            )
                            # Validar antes de crear
                            bag.full_clean()
                            # Usar bulk_create para evitar el signal que intenta usar Celery
                            Bag.objects.bulk_create([bag], ignore_conflicts=False)
                            # Obtener el Bag recién creado usando los campos únicos
                            bag = Bag.objects.filter(
                                user=invite_user,
                                type="INVITED",
                                academy=cohort.academy,
                                status="PAID",
                                was_delivered=False,
                            ).order_by("-id").first()
                            if not bag:
                                raise Exception("No se pudo crear el Bag - no se encontró después de bulk_create")
                            self.stdout.write(
                                self.style.SUCCESS(f"   ✅ Bag creado directamente en BD (ID: {bag.id})")
                            )
                        else:
                            raise

                    bag.plans.add(plan)

                    # Obtener precio del plan
                    financing_option = plan.financing_options.filter(how_many_months=1).first()
                    if not financing_option:
                        self.stdout.write(
                            self.style.ERROR("   ❌ No se encontró financing_option para 1 mes")
                        )
                        bag.delete()
                        error_count += 1
                        continue

                    plan_price = financing_option.monthly_price
                    is_free = plan_price == 0

                    externally_managed = invite.payment_method is not None

                    # Crear ProofOfPayment si es necesario
                    proof = None
                    if invite.payment_method and not invite.payment_method.is_crypto:
                        if not invite.author:
                            self.stdout.write(
                                self.style.WARNING(
                                    "   ⚠️  No hay author en la invitación, usando usuario del sistema"
                                )
                            )
                            # Usar el usuario del sistema o el usuario de la invitación como fallback
                            author = invite_user if hasattr(invite_user, "is_staff") else None
                            if not author:
                                self.stdout.write(
                                    self.style.ERROR("   ❌ No se puede determinar el author para ProofOfPayment")
                                )
                                bag.delete()
                                error_count += 1
                                continue

                        proof = ProofOfPayment(
                            created_by=invite.author or invite_user,
                            status=ProofOfPayment.Status.DONE,
                            provided_payment_details=f"Payment via invitation with payment method: {invite.payment_method.title}",
                            reference=f"INVITE-{invite.id}",
                        )
                        proof.save()

                    # Crear Invoice
                    invoice = Invoice(
                        amount=plan_price,
                        paid_at=utc_now,
                        user=invite_user,
                        bag=bag,
                        academy=bag.academy,
                        status="FULFILLED",
                        currency=bag.academy.main_currency,
                        payment_method=invite.payment_method,
                        externally_managed=externally_managed,
                        proof=proof,
                    )
                    invoice.save()

                    # Ejecutar task para crear PlanFinancing
                    payments_tasks.build_plan_financing.delay(bag.id, invoice.id, is_free=is_free)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Bag creado (ID: {bag.id}), Invoice creado (ID: {invoice.id}), "
                            f"task build_plan_financing encolado"
                        )
                    )
                    fixed_count += 1
                    users_with_plans_created.append(
                        {
                            "user": user,
                            "plan": plan_name,
                            "cohort": cohort.name if cohort else None,
                            "bag_id": bag.id,
                            "invoice_id": invoice.id,
                        }
                    )

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error al crear Bag: {str(e)}"))
                    error_count += 1
                    import traceback

                    self.stdout.write(traceback.format_exc())

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("Resumen:")
        self.stdout.write(f"  ✅ Bags creados/fixeados: {fixed_count}")
        self.stdout.write(f"  ⚠️  Saltados: {skipped_count}")
        self.stdout.write(f"  ❌ Errores: {error_count}")
        self.stdout.write(f"{'='*80}\n")

        # Mostrar lista ordenada de usuarios a los que se creó el plan
        if users_with_plans_created:
            self.stdout.write(f"\n{'='*80}")
            self.stdout.write(
                self.style.SUCCESS(f"USUARIOS A LOS QUE SE CREÓ EL PLAN ({len(users_with_plans_created)}):")
            )
            self.stdout.write(f"{'='*80}\n")

            # Ordenar por nombre completo
            users_with_plans_created.sort(
                key=lambda x: f"{x['user'].first_name or ''} {x['user'].last_name or ''} {x['user'].email}"
            )

            for idx, user_info in enumerate(users_with_plans_created, 1):
                user = user_info["user"]
                plan = user_info["plan"]
                cohort = user_info.get("cohort")
                bag_id = user_info.get("bag_id")
                invoice_id = user_info.get("invoice_id")

                self.stdout.write(
                    f"{idx}. {user.first_name} {user.last_name} ({user.email})"
                )
                self.stdout.write(f"   - Plan: {plan}")
                if cohort:
                    self.stdout.write(f"   - Cohort: {cohort}")
                if bag_id:
                    self.stdout.write(f"   - Bag ID: {bag_id}")
                if invoice_id:
                    self.stdout.write(f"   - Invoice ID: {invoice_id}")
                self.stdout.write("")

            self.stdout.write(f"{'='*80}\n")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nEste fue un DRY-RUN. Ejecuta sin --dry-run para crear los Bags realmente."
                )
            )
