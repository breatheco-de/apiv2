# Financing Plan Seats – Implementation Changelog

## Overview

This changelog documents the new seat-management capabilities added to plan financings.  
Objective: align financing seats with subscription seats (team ownership, per-seat/per-team strategies, consumable issuance, auto-recharge, and API surface).

## Data Model Changes

- **`PlanFinancingTeam`** (one-to-one with `PlanFinancing`)
  - Tracks `additional_seats`, `consumption_strategy` (PER_SEAT | PER_TEAM), and `seats_log`.
  - Owner seat auto-created on financing save when a seat-bearing service is present.
- **`PlanFinancingSeat`** (many-to-one to `PlanFinancingTeam`)
  - Stores `user`, `email`, `is_active`, `seat_log` with uniqueness constraints per team.
  - Added convenience `billing_team` property for parity with subscription seats.
- **`Consumable` / `ServiceStockScheduler`**
  - New FKs: `plan_financing_team`, `plan_financing_seat`.
  - Query helpers (`Consumable.list`, spend tracking) updated to include financing seats/teams.
- **Migration `0019`**
  - Creates new tables and wiring, adds fields to existing models.

## Business Logic

- **PlanFinancing.auto_sync_team**
  - Creates/updates teams and the owner seat, mirrors subscription flows.
  - Team strategy defaults to plan consumption strategy; BOTH collapses to PER_SEAT.
- **Seat operations (`payments/actions.py`)**
  - `create_plan_financing_seat`, `replace_plan_financing_seat`, `deactivate_plan_financing_seat`.
  - Shared validation (`validate_seats_limit`) now supports financing teams.
  - Grant capabilities to assigned users per plan; regenerate consumables when seats change.
- **Consumable ownership**
  - `get_user_from_consumable_to_be_charged` handles financing seats/teams and per-seat/per-team contexts.
  - Auto-recharge validations now respect plan-financing seats and allow recharge when enabled.
- **Service stock scheduler**
  - `build_service_stock_scheduler_from_plan_financing` issues schedulers per seat or team based on strategy.
  - `renew_consumables` copies financing seat/team metadata into new consumables and preserves user assignment.

## API Surface

New V2 endpoints (parity with subscription team endpoints):

| Route | Method(s) | Description |
|-------|-----------|-------------|
| `/v2/payments/plan-financing/<id>/team` | GET | Returns financing team summary |
| `/v2/payments/plan-financing/<id>/team/seat` | GET, PUT | List seats, add/replace seats via `add_seats` / `replace_seats` payloads |
| `/v2/payments/plan-financing/<id>/team/seat/<seat_id>` | DELETE | Deactivate a seat (frees slot, clears consumables) |

Owner authentication mirrors subscriptions: only the financing owner can manage seats.

## Auto-Recharge Integration

- Plan financings reuse `AbstractIOweYou` auto-recharge fields (`auto_recharge_enabled`, thresholds, limits).
- Spend aggregation counts invoices tied to financing seats/teams.
- `process_auto_recharge` charges the owner but includes financing context when generating consumables.

## Documentation Updates

- `docs/LLM-DOCS/SEATS_AND_TEAMS.md`
  - Added “Plan Financing Seats” section describing endpoints, strategies, and auto-recharge behavior.

## Testing

New pytest coverage: `breathecode/payments/tests/views/tests_plan_financing_seat_view.py`

- Validates team retrieval, seat listing, add/replace seat workflows, and seat deletion.
- Uses APIRequestFactory + mocking to isolate view logic.

## Follow-Ups / Considerations

- Invitations for financing seats (similar to subscription pending invites) are not yet implemented.
- Monitor auto-recharge spend calculations now that financings share the subscription logic branch.

