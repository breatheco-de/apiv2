# Service Deprovision System

This document explains how service deprovision works in BreatheCode: where it starts, how entitlement is re-validated, how app-specific handlers are resolved, and how safety nets (supervisors) prevent drift.

## Overview

Service deprovision is the process that removes external access when a user loses entitlement for a service.

Core goals:

1. **Do not remove access too early**
   - Before deprovisioning, the system checks if the user still has consumables for the same service from any valid source.
2. **Delegate deprovision logic to each domain**
   - Payments emits a generic deprovision signal.
   - Each app (for example provisioning/LLM) registers its own handler.
3. **Be resilient**
   - Tasks re-check entitlement before destructive calls.
   - Supervisors detect state drift and self-heal.

---

## High-Level Architecture

The flow is signal-driven:

1. A billing entity (Subscription or PlanFinancing) becomes `EXPIRED`/`DEPRECATED`.
2. Payments emits `deprovision_service` for impacted services.
3. Provisioning receiver validates current entitlement using `Consumable.list(...)`.
4. If entitlement is gone, it resolves a registered deprovisioner by service slug.
5. The deprovisioner triggers a service-specific task (for LLM: delete user in LiteLLM).

---

## Trigger Sources in Payments

Deprovision signal emission currently happens in model `save()` transitions.

### 1) Subscription transition

When a subscription changes status to `EXPIRED` or `DEPRECATED`, it emits deprovision for:

- subscription-level service items (`subscription.service_items`)
- plan-level items (`PlanServiceItem` from `subscription.plans`)

It deduplicates with `service_ids` to avoid duplicate signals.

```2605:2625:/workspaces/apiv2/breathecode/payments/models.py
            if self.status in [self.Status.EXPIRED, self.Status.DEPRECATED]:
                service_ids: set[int] = set()
                for service_item in self.service_items.select_related("service").all():
                    service = service_item.service
                    if service.id in service_ids:
                        continue
                    service_ids.add(service.id)
                    signals.deprovision_service.send_robust(
                        sender=Service, instance=service, user_id=self.user.id, context={}
                    )
                for plan in self.plans.all():
                    for plan_service_item in PlanServiceItem.objects.select_related("service_item__service").filter(
                        plan=plan
                    ):
                        service = plan_service_item.service_item.service
                        if service.id in service_ids:
                            continue
                        service_ids.add(service.id)
                        signals.deprovision_service.send_robust(
                            sender=Service, instance=service, user_id=self.user.id, context={}
                        )
```

### 2) PlanFinancing transition

When a plan financing changes status to `EXPIRED` or `DEPRECATED`, it emits deprovision for plan service items (also deduplicated by `service_ids`).

```2396:2412:/workspaces/apiv2/breathecode/payments/models.py
            if self.status in [self.Status.EXPIRED, self.Status.DEPRECATED]:
                # Deprovision external services when the financing is fully expired/deprecated.
                service_ids: set[int] = set()
                for plan in self.plans.all():
                    for plan_service_item in PlanServiceItem.objects.select_related("service_item__service").filter(
                        plan=plan
                    ):
                        service = plan_service_item.service_item.service
                        if service.id in service_ids:
                            continue
                        service_ids.add(service.id)
                        signals.deprovision_service.send_robust(
                            sender=Service,
                            instance=service,
                            user_id=self.user.id,
                            context={},
                        )
```

---

## Receiver Gate (Critical Safety Check)

Provisioning app listens to the generic signal and performs a universal gate:

- if user still has consumables for that same `Service`, skip deprovision.
- only deprovision when balance/entitlement is truly gone.

```39:58:/workspaces/apiv2/breathecode/provisioning/receivers.py
@receiver(deprovision_service, sender=Service)
def deprovision_service_receiver(sender: Type[Service], instance: Service, user_id: int, context: dict, **kwargs):
    ...
    service_slug = instance.slug

    consumables = Consumable.list(user=user, service=instance)
    if consumables.exists():
        logger.info(f"User {user_id} still has consumables for service {service_slug}, skipping deprovisioning.")
        return

    deprovisioner = get_service_deprovisioner(service_slug)
    if deprovisioner:
        return deprovisioner(user_id=user_id, context=context or {})
```

Why this matters:

- A user can hold the same service from another active subscription/financing/team seat.
- This gate prevents accidental deprovision caused by one resource expiring while another remains valid.

---

## Deprovisioner Registry

Handlers are registered by service slug with decorator:

- `@service_deprovisioner("service_slug")`

Registry implementation:

```10:31:/workspaces/apiv2/breathecode/utils/decorators/service_deprovisioner.py
def service_deprovisioner(service_slug: str):
    ...
    def decorator(fn: Callable) -> Callable:
        if service_slug in _deprovisioners_registry:
            raise ValidationException(f"Service deprovisioner for {service_slug} already registered")
        _deprovisioners_registry[service_slug] = fn
        return fn
    return decorator

def get_service_deprovisioner(service_slug: str) -> Callable | None:
    return _deprovisioners_registry.get(service_slug)
```

Design notes:

- One handler per service slug.
- Service-specific logic stays close to domain code.

---

## Example: LLM Deprovision

LLM registers handler for `free_monthly_llm_budget`, which schedules async deprovision task:

```1168:1169:/workspaces/apiv2/breathecode/provisioning/actions.py
    deprovision_litellm_user_task.delay(user_id=user_id)
```

Task behavior:

1. Abort if local user does not exist.
2. Skip if user still has LLM consumable.
3. Group `ProvisioningLLM` records by `(academy_id, vendor_id)`.
4. Call LiteLLM `delete_user`.
5. Update local rows to `DEPROVISIONED` or `ERROR`.

```600:679:/workspaces/apiv2/breathecode/provisioning/tasks.py
@task(priority=TaskPriority.STUDENT.value)
def deprovision_litellm_user_task(user_id: int, **_: Any):
    ...
    if Consumable.list(user=user, service="free_monthly_llm_budget").exists():
        logger.info(f"User {user_id} still has free_monthly_llm_budget, skipping deprovision")
        return
    ...
    client.delete_user(user_ids=user_id_list)
    ...
    ProvisioningLLM.objects.filter(...).update(
        status=ProvisioningLLM.STATUS_DEPROVISIONED,
        deprovisioned_at=now,
        error_message="",
        updated_at=timezone.now(),
    )
```

---

## Supervisor Safety Net (Drift Repair)

Signals can be missed due to transient failures, timing issues, or manual state changes.
Supervisor-based healing covers these cases.

For LLM:

- `supervise_llm_users_without_budget` scans active `ProvisioningLLM` users.
- If a user has no LLM budget consumable, opens issue `llm-user-missing-budget`.
- Issue handler revalidates state and schedules deprovision task.

```11:48:/workspaces/apiv2/breathecode/provisioning/supervisors.py
@supervisor(delta=timedelta(hours=6))
def supervise_llm_users_without_budget():
    ...

@issue(supervise_llm_users_without_budget, delta=timedelta(minutes=15), attempts=3)
def llm_user_missing_budget(user_id: int):
    ...
    deprovision_litellm_user_task.delay(user_id=user_id)
    return None
```

---

## Idempotency and Reliability Rules

The current design is intentionally defensive:

1. **Signal receiver checks consumables before deprovision.**
2. **Domain task rechecks entitlement before external deletion.**
3. **Supervisor issue handler rechecks before scheduling.**
4. **Failure path updates local status (`ERROR`) and retries via task manager.**

This triple-check pattern is what keeps deprovision safe under retries and concurrency.

---

## Troubleshooting Guide

### Case A: User should be deprovisioned, but still has access

Check:

1. Did billing transition to `EXPIRED/DEPRECATED` and emit signal?
2. Did receiver run and resolve a deprovisioner for this service slug?
3. Did receiver skip because `Consumable.list(...).exists()` was true?
4. Did deprovision task run and succeed (`ProvisioningLLM` -> `DEPROVISIONED`)?
5. If not, is there a supervisor issue pending (`llm-user-missing-budget`)?

### Case B: User was deprovisioned unexpectedly

Check:

1. Whether user actually had an active consumable for the exact service instance.
2. Whether service slug registered in deprovisioner matches the service emitted by payments.
3. Whether upstream deletion was triggered by another academy/vendor scope.

### Case C: No handler found for a service

Receiver logs:

- `No deprovisioner found for service <slug>`

Fix:

- register a handler with `@service_deprovisioner("<slug>")` in the owning app.

---

## Recommended Practices for New Service Deprovisioners

When adding a new external service integration:

1. Register a dedicated deprovisioner by service slug.
2. Keep handler minimal: enqueue a task, do not perform heavy network logic inline.
3. In task, re-check entitlement before deleting external resources.
4. Persist external error details to local status fields for observability.
5. Add a supervisor for drift if missing deprovision has non-trivial cost/risk.
