# Plan financing consumables — prune command

Operational reference for cleaning **duplicate or ahead-of-schedule consumables** on `PlanFinancing` contracts. Use this as the baseline if you need new database cleanup around consumables: extend this command or reuse its helpers in `breathecode/payments/actions.py` instead of inventing a parallel flow.

## Problem it solves

Plan financing renews consumables monthly via `charge_plan_financing` → `renew_plan_financing_consumables` → `renew_consumables`. Bugs or double-renew (e.g. catch-up + charge both renewing) can leave **extra `Consumable` rows** whose `valid_until` falls in a **future billing period** the user has not paid for yet.

Those extras inflate balances in admin and can confuse VPS / LLM alignment. They are **not** the same as expired rows (`valid_until` in the past), which the command intentionally ignores in the listing.

## Command

```bash
python manage.py prune_plan_consumables --plan-slug <catalog-plan-slug> [options]
# or
python manage.py prune_plan_consumables --plan-id <catalog-plan-id> [options]
```

**Module:** `breathecode/payments/management/commands/prune_plan_consumables.py`

### Arguments

| Flag | Description |
|------|-------------|
| `--plan-slug` | Catalog `Plan.slug` (all `PlanFinancing` linked to that plan). |
| `--plan-id` | Catalog `Plan.id` (alternative to slug; use one, not both). |
| `--email` | Limit to one user email. |
| `--plan-financing-id` | Limit to a single `PlanFinancing` id. |
| `--yes` | Delete without interactive `y/N` prompt. |

### Who is processed

Only plan financings where **`plan_financing_caps_consumables_at_next_payment`** is true:

- `status != FULLY_PAID`
- `installments_paid < how_many_installments`

`FULLY_PAID` or all installments paid → skipped (no prune).

### What is listed

For each eligible financing:

1. **Expired consumables** (`valid_until` before today’s calendar date) → not listed (“vencidos”).
2. **Active consumables** → sorted by `valid_until`, tagged:
   - **KEEP** (green): `valid_until` on or before the grace cutoff.
   - **DELETE** (red): `valid_until` after the grace cutoff.

### Delete rule (grace day)

Helpers: `consumable_valid_until_exceeds_next_payment`, `plan_financing_consumable_prune_cutoff_date` in `breathecode/payments/actions.py`.

Cutoff date = **`next_payment_at` calendar date + 1 day**.

| `next_payment_at` | Example `valid_until` | Action |
|-------------------|----------------------|--------|
| 2026-09-26 | 2026-09-26 (any time) | KEEP |
| 2026-09-26 | 2026-09-27 | KEEP (grace day; VPS credits often end here) |
| 2026-09-26 | 2026-09-28 or later | DELETE |

Comparison uses **calendar days**, not exact clock time (so 17:43 on the same day as `next_payment_at` at 05:43 still KEEP).

### Interactive flow

1. Prints plan slug/id and each financing block.
2. Lists KEEP then DELETE per financing.
3. Asks `Delete these consumables? [y/N]` unless `--yes`.
4. On confirm: deletes only DELETE rows; resets `ServiceStockScheduler.valid_until` that were past cutoff back to `next_payment_at`.

### Cascade on delete

Django `delete()` may remove related rows. The command reports consumable count separately and lists cascade breakdown:

| Model | Effect |
|-------|--------|
| `payments.Consumable` | Rows explicitly selected for DELETE. |
| `payments.ConsumptionSession` | CASCADE — usage sessions tied to those consumables. |
| `payments.servicestockscheduler_consumables` | M2M link rows removed (schedulers stay). |

**Not deleted:** `ProvisioningVPS` (`consumed_consumable` is `SET_NULL` only). KEEP consumibles (current period + grace) remain, including VPS-linked credits.

## Related runtime behavior (prevention)

While installments remain unpaid, `renew_consumables` caps new stock at `next_payment_at` by calendar day and skips duplicate issuance on the same day (`actions.cap_plan_financing_valid_until_at_next_payment`). See `.cursor/rules/02-backend.mdc` (`charge_plan_financing` / `created_by_admin`).

For staff catch-up charges without double-renew, see `backfill_plan_financing_created_by_admin` (charge renews once; catch-up does not call renew again).

## Other useful commands (same domain)

| Command | Use |
|---------|-----|
| `diagnose_scheduler --scheduler-id <id>` | Why a scheduler is not issuing consumables. |
| `backfill_plan_financing_created_by_admin --plans <slugs>` | Admin-managed financing catch-up (charges, not prune). |
| `renew_consumables` (cron / management) | Scheduled renewal; different from prune. |

## Tests

`breathecode/payments/tests/management/commands/tests_prune_plan_consumables.py`

## Extending this for new cleanup

When adding new consumable cleanup:

1. Reuse `consumable_valid_until_exceeds_next_payment`, `consumable_valid_until_is_expired`, and `plan_financing_caps_consumables_at_next_payment` from `actions.py`.
2. Prefer extending `prune_plan_consumables` (new flags, filters) over a second delete command with different rules.
3. Always list before delete; keep interactive confirm unless `--yes` for automation.
4. Document cascade impact and update this file.

## Example (production)

```bash
heroku run bash --app breathecode
python manage.py prune_plan_consumables \
  --plan-slug plan-apoyo-profesional-ai-engineering \
  --email student@example.com
```

Review KEEP/DELETE, confirm with `y` only if DELETE rows are clearly the next unpaid month (e.g. October when `next_payment_at` is late September).
