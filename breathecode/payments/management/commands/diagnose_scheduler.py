"""
Management command para diagnosticar por qué no se están generando consumibles
para un ServiceStockScheduler específico.

Uso:
    python manage.py diagnose_scheduler --scheduler-id 31753
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from breathecode.payments.models import (
    ServiceStockScheduler,
    Subscription,
    PlanFinancing,
    Consumable,
)
from breathecode.payments import actions


class Command(BaseCommand):
    help = "Diagnosticar por qué no se están generando consumibles para un scheduler"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scheduler-id",
            type=int,
            required=True,
            help="ID del ServiceStockScheduler a diagnosticar",
        )
        parser.add_argument(
            "--force-renew",
            action="store_true",
            help="Intentar forzar la renovación después del diagnóstico",
        )
        parser.add_argument(
            "--fix-resource",
            action="store_true",
            help="Intentar copiar el recurso del Plan al Plan Financing si falta",
        )

    def handle(self, *args, **options):
        scheduler_id = options["scheduler_id"]
        force_renew = options.get("force_renew", False)

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS(f"🔍 DIAGNÓSTICO: ServiceStockScheduler #{scheduler_id}"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}\n"))

        # 1. Verificar que el scheduler existe
        scheduler = ServiceStockScheduler.objects.filter(id=scheduler_id).first()
        if not scheduler:
            self.stdout.write(self.style.ERROR(f"❌ ServiceStockScheduler con ID {scheduler_id} no encontrado"))
            return

        self.stdout.write(self.style.SUCCESS(f"✅ Scheduler encontrado\n"))

        # 2. Información básica del scheduler
        self.print_scheduler_info(scheduler)

        # 3. Verificar condiciones de renovación
        issues = self.check_renewal_conditions(scheduler)

        # 4. Verificar consumibles existentes
        self.check_existing_consumables(scheduler)

        # 5. Resumen y recomendaciones
        self.print_summary(issues, scheduler)

        # 6. Intentar corregir recurso faltante si se solicita
        if options.get("fix_resource"):
            if self.fix_missing_resource(scheduler):
                # Si se corrigió, verificar de nuevo
                self.stdout.write("\n" + "=" * 70)
                self.stdout.write("🔄 VERIFICANDO NUEVAMENTE DESPUÉS DE LA CORRECCIÓN")
                self.stdout.write("=" * 70 + "\n")
                issues = self.check_renewal_conditions(scheduler)
                self.print_summary(issues, scheduler)

        # 7. Intentar renovar si se solicita
        if force_renew:
            if not issues or options.get("fix_resource"):
                self.attempt_renewal(scheduler)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  No se puede renovar porque hay problemas pendientes. "
                        "Usa --fix-resource primero si falta un recurso."
                    )
                )

    def print_scheduler_info(self, scheduler):
        """Imprimir información básica del scheduler"""
        self.stdout.write(self.style.SUCCESS("📋 INFORMACIÓN DEL SCHEDULER:"))
        self.stdout.write(f"  ID: {scheduler.id}")
        self.stdout.write(f"  valid_until: {scheduler.valid_until or 'None'}")
        self.stdout.write(f"  plan_handler: {scheduler.plan_handler_id or 'None'}")
        self.stdout.write(f"  subscription_handler: {scheduler.subscription_handler_id or 'None'}")
        self.stdout.write(f"  subscription_seat: {scheduler.subscription_seat_id or 'None'}")
        self.stdout.write(f"  subscription_billing_team: {scheduler.subscription_billing_team_id or 'None'}")
        self.stdout.write(f"  plan_financing_seat: {scheduler.plan_financing_seat_id or 'None'}")
        self.stdout.write(f"  plan_financing_team: {scheduler.plan_financing_team_id or 'None'}\n")

    def check_renewal_conditions(self, scheduler):
        """Verificar todas las condiciones que pueden impedir la renovación"""
        issues = []
        utc_now = timezone.now()

        self.stdout.write(self.style.SUCCESS("🔍 VERIFICANDO CONDICIONES DE RENOVACIÓN:\n"))

        # Verificar plan_handler con subscription
        if scheduler.plan_handler and scheduler.plan_handler.subscription:
            subscription = scheduler.plan_handler.subscription
            self.stdout.write(f"📌 Plan Handler -> Subscription #{subscription.id}")

            # Verificar valid_until
            if subscription.valid_until and subscription.valid_until < utc_now:
                issues.append(
                    f"❌ La suscripción {subscription.id} está vencida (valid_until: {subscription.valid_until})"
                )
                self.stdout.write(self.style.ERROR(f"  ❌ VENCIDA: valid_until={subscription.valid_until} < now={utc_now}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Válida: valid_until={subscription.valid_until or 'None'} >= now={utc_now}")
                )

            # Verificar next_payment_at
            if subscription.next_payment_at < utc_now:
                issues.append(
                    f"❌ La suscripción {subscription.id} necesita ser pagada (next_payment_at: {subscription.next_payment_at})"
                )
                self.stdout.write(
                    self.style.ERROR(f"  ❌ PAGO PENDIENTE: next_payment_at={subscription.next_payment_at} < now={utc_now}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Pago al día: next_payment_at={subscription.next_payment_at} >= now={utc_now}")
                )

            # Verificar status
            self.stdout.write(f"  Status: {subscription.status}")
            if subscription.status in [
                Subscription.Status.DEPRECATED,
                Subscription.Status.EXPIRED,
                Subscription.Status.PAYMENT_ISSUE,
            ]:
                issues.append(f"❌ La suscripción {subscription.id} tiene status inválido: {subscription.status}")
                self.stdout.write(self.style.ERROR(f"  ❌ STATUS INVÁLIDO: {subscription.status}"))

            # Verificar service_item
            if scheduler.plan_handler.handler:
                service_item = scheduler.plan_handler.handler.service_item
                self.stdout.write(f"  Service Item: {service_item.id} - {service_item}")
                self.stdout.write(f"    is_renewable: {service_item.is_renewable}")
                self.stdout.write(f"    renew_at: {service_item.renew_at} {service_item.renew_at_unit}")

                if not service_item.is_renewable:
                    issues.append(f"⚠️  El service item {service_item.id} no es renovable (is_renewable=False)")

                # Verificar recurso vinculado
                service = service_item.service
                self.stdout.write(f"    Service: {service.slug} (type: {service.type})")

                if service.type != "VOID":
                    resource_key = service.type.lower()
                    resource_value = getattr(subscription, f"selected_{resource_key}", None)
                    if not resource_value:
                        issues.append(
                            f"❌ El plan no tiene un recurso vinculado para el servicio {service.slug} (type: {service.type})"
                        )
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ SIN RECURSO: subscription.selected_{resource_key} = None")
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ Recurso vinculado: {resource_key} = {resource_value.id}")
                        )

            self.stdout.write("")

        # Verificar plan_handler con plan_financing
        elif scheduler.plan_handler and scheduler.plan_handler.plan_financing:
            # Recargar desde la base de datos para obtener relaciones
            plan_financing = (
                PlanFinancing.objects.select_related("selected_mentorship_service_set", "selected_cohort_set", "selected_event_type_set")
                .prefetch_related("plans")
                .get(id=scheduler.plan_handler.plan_financing.id)
            )
            self.stdout.write(f"📌 Plan Handler -> Plan Financing #{plan_financing.id}")

            # Verificar plan_expires_at
            if plan_financing.plan_expires_at and plan_financing.plan_expires_at < utc_now:
                issues.append(
                    f"❌ El plan financing {plan_financing.id} está vencido (plan_expires_at: {plan_financing.plan_expires_at})"
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ VENCIDO: plan_expires_at={plan_financing.plan_expires_at} < now={utc_now}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ Válido: plan_expires_at={plan_financing.plan_expires_at or 'None'} >= now={utc_now}"
                    )
                )

            # Verificar next_payment_at
            if (
                plan_financing.status == PlanFinancing.Status.ACTIVE
                and plan_financing.next_payment_at < utc_now
            ):
                issues.append(
                    f"❌ El plan financing {plan_financing.id} necesita ser pagado (next_payment_at: {plan_financing.next_payment_at})"
                )
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ PAGO PENDIENTE: next_payment_at={plan_financing.next_payment_at} < now={utc_now}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅ Pago al día: next_payment_at={plan_financing.next_payment_at}, status={plan_financing.status}"
                    )
                )

            # Verificar status
            self.stdout.write(f"  Status: {plan_financing.status}")
            if plan_financing.status in [
                PlanFinancing.Status.CANCELLED,
                PlanFinancing.Status.DEPRECATED,
                PlanFinancing.Status.EXPIRED,
            ]:
                issues.append(f"❌ El plan financing {plan_financing.id} tiene status inválido: {plan_financing.status}")
                self.stdout.write(self.style.ERROR(f"  ❌ STATUS INVÁLIDO: {plan_financing.status}"))

            # Verificar service_item
            if scheduler.plan_handler.handler:
                service_item = scheduler.plan_handler.handler.service_item
                self.stdout.write(f"  Service Item: {service_item.id} - {service_item}")
                self.stdout.write(f"    is_renewable: {service_item.is_renewable}")

                if not service_item.is_renewable:
                    issues.append(
                        f"⚠️  El service item {service_item.id} no es renovable (is_renewable=False). "
                        "Los consumibles NO se renovarán automáticamente, pero el primer consumible debería crearse."
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  NO RENOVABLE: is_renewable=False - Los consumibles NO se renovarán automáticamente"
                        )
                    )
                else:
                    self.stdout.write(self.style.SUCCESS(f"  ✅ RENOVABLE: is_renewable=True"))

                # Verificar recurso vinculado (CRÍTICO para crear el primer consumible)
                service = service_item.service
                self.stdout.write(f"    Service: {service.slug} (type: {service.type})")

                if service.type != "VOID":
                    resource_key = service.type.lower()
                    resource_value = getattr(plan_financing, f"selected_{resource_key}", None)
                    
                    # Mostrar información del recurso
                    if resource_value:
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ Recurso vinculado: {resource_key} = {resource_value.id} ({resource_value})")
                        )
                    else:
                        # Verificar si el plan tiene el recurso configurado
                        plans = plan_financing.plans.all()
                        plan_has_resource = False
                        plan_ids_with_resource = []
                        
                        for plan in plans:
                            plan_resource = getattr(plan, resource_key, None)
                            if plan_resource:
                                plan_has_resource = True
                                plan_ids_with_resource.append(plan.id)
                        
                        if plan_has_resource:
                            issues.append(
                                f"❌ CRÍTICO: El plan financing {plan_financing.id} NO tiene un recurso vinculado "
                                f"para el servicio {service.slug} (type: {service.type}), "
                                f"PERO los planes {', '.join(map(str, plan_ids_with_resource))} SÍ tienen el recurso configurado. "
                                "El plan financing debería heredar el recurso del plan."
                            )
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ❌ SIN RECURSO en Plan Financing: plan_financing.selected_{resource_key} = None"
                                )
                            )
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ⚠️  PERO los Planes {', '.join(map(str, plan_ids_with_resource))} SÍ tienen {resource_key} configurado"
                                )
                            )
                        else:
                            issues.append(
                                f"❌ CRÍTICO: El plan financing {plan_financing.id} NO tiene un recurso vinculado "
                                f"para el servicio {service.slug} (type: {service.type}). "
                                "El primer consumible NO se puede crear sin esto."
                            )
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ❌ SIN RECURSO: plan_financing.selected_{resource_key} = None - "
                                    "El consumible NO se puede crear sin un recurso vinculado"
                                )
                            )
                            # Mostrar IDs de los planes asociados
                            plan_ids = list(plans.values_list("id", flat=True))
                            if plan_ids:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  📋 Planes asociados al Plan Financing: {', '.join(map(str, plan_ids))}"
                                    )
                                )
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  💡 Verifica si alguno de estos planes tiene {resource_key} configurado"
                                    )
                                )

            self.stdout.write("")

        # Verificar subscription_handler
        elif scheduler.subscription_handler:
            subscription = scheduler.subscription_handler.subscription
            self.stdout.write(f"📌 Subscription Handler -> Subscription #{subscription.id}")

            # Verificar valid_until
            if subscription.valid_until and subscription.valid_until < utc_now:
                issues.append(
                    f"❌ La suscripción {subscription.id} está vencida (valid_until: {subscription.valid_until})"
                )
                self.stdout.write(
                    self.style.ERROR(f"  ❌ VENCIDA: valid_until={subscription.valid_until} < now={utc_now}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Válida: valid_until={subscription.valid_until or 'None'} >= now={utc_now}")
                )

            # Verificar next_payment_at
            if subscription.next_payment_at < utc_now:
                issues.append(
                    f"❌ La suscripción {subscription.id} necesita ser pagada (next_payment_at: {subscription.next_payment_at})"
                )
                self.stdout.write(
                    self.style.ERROR(f"  ❌ PAGO PENDIENTE: next_payment_at={subscription.next_payment_at} < now={utc_now}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Pago al día: next_payment_at={subscription.next_payment_at} >= now={utc_now}")
                )

            self.stdout.write("")

        else:
            issues.append("❌ El scheduler no tiene ningún handler asociado (plan_handler o subscription_handler)")
            self.stdout.write(self.style.ERROR("  ❌ SIN HANDLER: No hay plan_handler ni subscription_handler"))

        # Verificar valid_until del scheduler
        self.stdout.write(f"📌 Scheduler valid_until: {scheduler.valid_until or 'None'}")
        if scheduler.valid_until and scheduler.valid_until > utc_now:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠️  El scheduler aún no necesita renovación (valid_until={scheduler.valid_until} > now={utc_now})"
                )
            )
            issues.append(
                f"⚠️  El scheduler aún no necesita renovación (valid_until={scheduler.valid_until} > now={utc_now})"
            )
        elif scheduler.valid_until and scheduler.valid_until <= utc_now:
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ El scheduler necesita renovación (valid_until={scheduler.valid_until} <= now={utc_now})")
            )
        else:
            self.stdout.write(self.style.WARNING("  ⚠️  El scheduler no tiene valid_until configurado"))

        self.stdout.write("")

        return issues

    def check_existing_consumables(self, scheduler):
        """Verificar consumibles existentes"""
        self.stdout.write(self.style.SUCCESS("📦 CONSUMIBLES EXISTENTES:\n"))

        consumables = scheduler.consumables.all().order_by("-id")
        count = consumables.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("  ⚠️  No hay consumibles asociados a este scheduler"))
        else:
            self.stdout.write(f"  Total: {count} consumible(s)\n")

            for i, consumable in enumerate(consumables[:5], 1):  # Mostrar solo los primeros 5
                self.stdout.write(f"  {i}. Consumable #{consumable.id}")
                self.stdout.write(f"     - how_many: {consumable.how_many}")
                self.stdout.write(f"     - valid_until: {consumable.valid_until or 'None'}")
                if consumable.user:
                    self.stdout.write(f"     - user: {consumable.user.email}")
                else:
                    self.stdout.write(f"     - user: None (team-owned)")

            if count > 5:
                self.stdout.write(f"  ... y {count - 5} más\n")

        self.stdout.write("")

    def print_summary(self, issues, scheduler):
        """Imprimir resumen y recomendaciones"""
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}\n"))

        if not issues:
            self.stdout.write(self.style.SUCCESS("✅ No se encontraron problemas. El scheduler debería poder generar consumibles."))
            self.stdout.write("\n💡 Para forzar la renovación, ejecuta:")
            self.stdout.write(f"   python manage.py diagnose_scheduler --scheduler-id {scheduler.id} --force-renew")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Se encontraron {len(issues)} problema(s):\n"))
            for i, issue in enumerate(issues, 1):
                self.stdout.write(f"  {i}. {issue}")

            self.stdout.write("\n💡 RECOMENDACIONES:")
            for issue in issues:
                if "sin recurso" in issue.lower() or "no tiene un recurso vinculado" in issue.lower():
                    self.stdout.write(
                        self.style.ERROR(
                            "  ❌ CRÍTICO: Asigna el recurso correspondiente al Plan Financing "
                            "(cohort, event_type, mentorship_service_set, etc.) para que se pueda crear el consumible"
                        )
                    )
                elif "no es renovable" in issue.lower() or "is_renewable=false" in issue.lower():
                    self.stdout.write(
                        self.style.WARNING(
                            "  ⚠️  Cambia is_renewable=True en el ServiceItem para que se renueven consumibles automáticamente"
                        )
                    )
                elif "vencida" in issue.lower() or "vencido" in issue.lower():
                    self.stdout.write("  - Verifica la fecha de expiración de la suscripción/plan financing")
                elif "pagada" in issue.lower() or "pagado" in issue.lower():
                    self.stdout.write("  - Procesa el pago pendiente de la suscripción/plan financing")
                elif "recurso vinculado" in issue.lower() and "crítico" not in issue.lower():
                    self.stdout.write("  - Asigna el recurso correspondiente al plan (cohort, event_type, etc.)")
                elif "renovable" in issue.lower() and "crítico" not in issue.lower():
                    self.stdout.write("  - Verifica que el service item tenga is_renewable=True")
                elif "valid_until" in issue.lower() and "scheduler" in issue.lower():
                    self.stdout.write("  - Espera a que el scheduler expire o ajusta la fecha si es necesario")

        self.stdout.write("")

    def attempt_renewal(self, scheduler):
        """Intentar forzar la renovación"""
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS("🔄 INTENTANDO RENOVACIÓN"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}\n"))

        from breathecode.payments.tasks import renew_consumables

        try:
            # Ejecutar la tarea de forma síncrona para ver errores
            renew_consumables(scheduler.id)
            self.stdout.write(self.style.SUCCESS("✅ Renovación ejecutada exitosamente"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al renovar: {str(e)}"))
            self.stdout.write(f"   Tipo: {type(e).__name__}")

    def fix_missing_resource(self, scheduler):
        """Intentar copiar el recurso del Plan al Plan Financing si falta"""
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS("🔧 INTENTANDO CORREGIR RECURSO FALTANTE"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}\n"))

        if not (scheduler.plan_handler and scheduler.plan_handler.plan_financing):
            self.stdout.write(self.style.ERROR("❌ Este scheduler no está asociado a un Plan Financing"))
            return False

        plan_financing = (
            PlanFinancing.objects.select_related("selected_mentorship_service_set", "selected_cohort_set", "selected_event_type_set")
            .prefetch_related("plans")
            .get(id=scheduler.plan_handler.plan_financing.id)
        )

        if not scheduler.plan_handler.handler:
            self.stdout.write(self.style.ERROR("❌ No se puede obtener el service item"))
            return False

        service_item = scheduler.plan_handler.handler.service_item
        service = service_item.service

        if service.type == "VOID":
            self.stdout.write(self.style.SUCCESS("✅ El servicio es VOID, no necesita recurso"))
            return True

        resource_key = service.type.lower()
        current_resource = getattr(plan_financing, f"selected_{resource_key}", None)

        if current_resource:
            self.stdout.write(
                self.style.SUCCESS(f"✅ El Plan Financing ya tiene {resource_key} = {current_resource.id}")
            )
            return True

        # Buscar el recurso en los planes asociados
        plans = plan_financing.plans.all()
        resource_found = None
        plan_with_resource = None

        for plan in plans:
            plan_resource = getattr(plan, resource_key, None)
            if plan_resource:
                resource_found = plan_resource
                plan_with_resource = plan
                break

        if not resource_found:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Ninguno de los planes asociados ({', '.join(map(str, plans.values_list('id', flat=True)))}) "
                    f"tiene {resource_key} configurado"
                )
            )
            return False

        # Copiar el recurso del plan al plan financing
        self.stdout.write(
            f"📋 Copiando {resource_key} del Plan #{plan_with_resource.id} al Plan Financing #{plan_financing.id}..."
        )
        setattr(plan_financing, f"selected_{resource_key}", resource_found)
        plan_financing.save(update_fields=[f"selected_{resource_key}"])

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Recurso copiado exitosamente: selected_{resource_key} = {resource_found.id} ({resource_found})"
            )
        )
        return True
