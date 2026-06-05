# Service Stock Status – Debug User Consumable Issues

This document explains how to use the **Service Stock Status** endpoint to debug why a student does not have the consumables they should have (e.g. mentorship sessions, event access, cohort access). The endpoint returns all **service stock schedulers** that should issue consumables for that user in the academy, plus diagnosis messages and optional balance.

---

## Endpoint

```
GET /v1/payments/academy/service/stock_status/<user_id>
```

- **`user_id`** (path, required): The student’s user ID.
- **Academy** (header, required): Academy ID (e.g. `Academy: 1`).
- **Permission:** Requires `read_service_stock_status` (sysadmin only; not granted to academy staff roles).

### Optional query parameter

| Parameter        | Values              | Description                                              |
|-----------------|---------------------|----------------------------------------------------------|
| `include_balance` | `true`, `1`, `y`    | If set, adds `consumables_balance` to the response (same shape as `GET /v1/payments/me/service/consumable`). Use it to compare “expected” vs “actual” balance. |

**Example:**

```bash
# Basic call – schedulers and issues only
GET /v1/payments/academy/service/stock_status/12345
Headers: Academy: 1, Authorization: Bearer <token>

# With current consumable balance (to compare with what schedulers should grant)
GET /v1/payments/academy/service/stock_status/12345?include_balance=true
Headers: Academy: 1, Authorization: Bearer <token>
```

---

## When to use it

- A student says they should have consumables (e.g. mentorship sessions) but don’t see them.
- You want to see **why** a given scheduler is not creating or renewing consumables (payment due, expired subscription, missing resource, etc.).
- You need the **scheduler id** to run the CLI diagnostic or force renewal (see below).

---

## Response shape

### Top level

| Field         | Type   | Description |
|---------------|--------|-------------|
| `user`        | object | `{ "id", "email" }` – the user you queried. |
| `academy_id`  | int    | Academy from the header. |
| `schedulers`  | array  | One object per **service stock scheduler** that can issue consumables for this user in this academy. |
| `consumables_balance` | object | Present only if `include_balance=true`. Same structure as `GET /v1/payments/me/service/consumable` (mentorship_service_sets, cohort_sets, event_type_sets, voids). |

### Each item in `schedulers`

| Field                  | Type    | Description |
|------------------------|---------|-------------|
| `id`                   | int     | **Scheduler id.** Use this with the CLI: `python manage.py diagnose_scheduler --scheduler-id <id>` (and optionally `--force-renew`, `--fix-resource`). |
| `source_type`          | string  | `"subscription"` or `"plan_financing"` – where this scheduler gets its plan/service from. |
| `source_id`            | int     | Subscription or PlanFinancing id. |
| `seat_id`              | int \| null | If the consumables are for a **seat** (not the subscription/plan owner), this is the subscription_seat or plan_financing_seat id. |
| `service`              | string  | Service slug (e.g. `mentorship-service`, `event-service`). |
| `service_item_id`      | int     | Service item id. |
| `renew_at`             | number  | Renewal interval (e.g. 1). |
| `renew_at_unit`        | string  | Unit (e.g. `MONTH`, `WEEK`). |
| `is_renewable`         | bool    | Whether the service item is set to auto-renew. |
| `scheduler_valid_until`| string (ISO) \| null | When the **next** refill is due. After this time, the renewal job should create a new consumable. |
| `resource_linked`      | bool    | **Important for debugging.** `true` if the subscription/plan financing has the required resource (e.g. `selected_mentorship_service_set`, `selected_cohort_set`, `selected_event_type_set`) for this service. If `false`, consumables often **cannot** be created until the resource is set or copied (e.g. with `--fix-resource`). |
| `consumables_count`    | int     | How many consumables this scheduler has already created. |
| `consumables_sample`   | array   | Last few consumables (id, how_many, valid_until, user_id). |
| `issues`               | array of strings | **Diagnosis:** reasons why renewal might be blocked (see below). |

---

## Understanding `issues`

Each scheduler’s `issues` array lists possible blockers. Use them to decide the next step.

### Subscription / plan financing status

- **"Subscription X is expired (valid_until: ...)"** – Subscription has ended. No consumables will be issued until the subscription is renewed or replaced.
- **"Subscription X needs to be paid (next_payment_at: ...)"** – Payment is overdue. Process payment for that subscription.
- **"Subscription X has invalid status: DEPRECATED | EXPIRED | PAYMENT_ISSUE"** – Subscription is in a bad state; fix or replace it.
- **"Plan financing X is expired (plan_expires_at: ...)"** – Same idea for plan financing.
- **"Plan financing X needs to be paid (next_payment_at: ...)"** – Payment due for plan financing.
- **"Plan financing X has invalid status: ..."** – Plan financing is CANCELLED, DEPRECATED, or EXPIRED.

### Resource (cohort / event type / mentorship set)

- **"Subscription has no linked resource for service X (type: ...)"** – The subscription does not have the required `selected_*` (e.g. cohort set, event type set, mentorship service set). Consumables for that service type need that resource.
- **"Plan financing X has no linked resource for service Y ..."** – Same for plan financing. If the message says **"but plans Z do"**, you can often fix it with:
  ```bash
  python manage.py diagnose_scheduler --scheduler-id <scheduler_id> --fix-resource
  ```

### Scheduler timing

- **"Scheduler does not need renewal yet (valid_until=... > now)"** – The next refill is in the future. No action unless you need to force an early refill (see below).
- **"Service item X is not renewable (is_renewable=False)"** – Auto-renewal is off; the first consumable may still exist, but no new ones will be created automatically.

### Other

- **"Scheduler has no plan_handler or subscription_handler"** – Scheduler is misconfigured; needs backend/data fix.

---

## Debugging workflow

1. **Call the endpoint**  
   `GET /v1/payments/academy/service/stock_status/<user_id>` (optionally with `?include_balance=true`).

2. **Confirm user and academy**  
   Check `user` and `academy_id` in the response.

3. **If `schedulers` is empty**  
   - User has no subscription/plan/seat in this academy that grants consumables, or  
   - Schedulers were never created (e.g. after adding a seat, the `build_service_stock_scheduler_*` task may not have run).  
   Check subscriptions/plan financings and seats for this user in this academy.

4. **For each scheduler that should grant the missing consumable**  
   - Read **`issues`**: fix expired/overdue/invalid subscription or plan financing, or missing resource.  
   - Check **`resource_linked`**: if `false`, consumables for that service often won’t be created until you set or copy the resource (e.g. `diagnose_scheduler --scheduler-id <id> --fix-resource`).  
   - Use **`id`** with the CLI for deeper checks or to force actions.

5. **Optional: run the CLI diagnostic**  
   ```bash
   python manage.py diagnose_scheduler --scheduler-id <scheduler_id>
   ```  
   This prints the same kind of checks in more detail. Add `--fix-resource` to copy the resource from the plan to the plan financing when applicable, or `--force-renew` to trigger a renewal (only if issues are resolved or acceptable).

6. **Compare with actual balance**  
   If you used `include_balance=true`, compare `consumables_balance` with what you expect from the schedulers (e.g. service slug, amounts). That shows whether the problem is “no consumables at all” vs “wrong service/resource/amount”.

---

## Example response (minimal)

```json
{
  "user": { "id": 12345, "email": "student@example.com" },
  "academy_id": 1,
  "schedulers": [
    {
      "id": 100,
      "source_type": "plan_financing",
      "source_id": 50,
      "seat_id": null,
      "service": "mentorship-service",
      "service_item_id": 3,
      "renew_at": 1,
      "renew_at_unit": "MONTH",
      "is_renewable": true,
      "scheduler_valid_until": "2025-03-15T00:00:00Z",
      "resource_linked": false,
      "consumables_count": 0,
      "consumables_sample": [],
      "issues": [
        "Plan financing 50 has no linked resource for mentorship-service (type: MENTORSHIP_SERVICE_SET), but plans [7] do; resource should be copied to plan financing."
      ]
    }
  ]
}
```

Here, the student has no consumables because **`resource_linked`** is `false`: the plan financing is missing the mentorship service set. The message says the plan has it; you can run:

```bash
python manage.py diagnose_scheduler --scheduler-id 100 --fix-resource
```

to copy the resource and then (if the scheduler is due) renewal can create the consumable.

---

## Related

- **Consumable balance (student view):** `GET /v1/payments/me/service/consumable`  
- **Academy consumables (staff):** `GET /v1/payments/academy/service/consumable?users=<user_id>` (includes staff-granted and subscription/plan consumables for that academy).  
- **CLI:** `python manage.py diagnose_scheduler --scheduler-id <id>` with optional `--fix-resource` and `--force-renew`.
