# prune_plan_consumables

Management command to list and delete **ahead-of-schedule** consumables on plan financings with unpaid installments.

```bash
python manage.py prune_plan_consumables --plan-slug <slug> [--email ...] [--plan-financing-id ...] [--yes]
```

**Full documentation** (rules, grace day, cascade, extension guide): [`apiv2/docs/agent-docs/PLAN_FINANCING_CONSUMABLES_PRUNE.md`](../../../docs/agent-docs/PLAN_FINANCING_CONSUMABLES_PRUNE.md)

**Implementation:** `management/commands/prune_plan_consumables.py`  
**Shared helpers:** `actions.py` — `consumable_valid_until_exceeds_next_payment`, `plan_financing_consumable_prune_cutoff_date`, `consumable_valid_until_is_expired`, `plan_financing_caps_consumables_at_next_payment`

When building new consumable cleanup commands, reuse those helpers and extend this command rather than duplicating delete logic.
