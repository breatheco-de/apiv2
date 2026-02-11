# Academy grant consumables endpoint – implementation checklist

Plan: `.cursor/plans/academy_grant_consumables_endpoint.plan.md`

| Step | Description | Status |
|------|-------------|--------|
| 1 | Consumable.standalone_invoice + migration, set at creation sites | Done |
| 2 | Extract shared helpers in actions.py | Done |
| 3 | Refactor validate_and_create_subscriptions to use shared helpers | Done |
| 4 | Add crud_consumable capability and assign to roles | Done |
| 5 | Add grant_consumables_for_user action | Done |
| 6 | Add AcademyGrantConsumableView and URL | Done |
| 7 | Fix/add unit tests for standalone_invoice and grant consumables | In progress |
| 8 | Document endpoint and payment method restriction | Done |

## Notes

- **Tests**: Payments test suite is currently failing at setup due to root `conftest.py` (`get_app_keys` → `linked_services.django.actions.get_app.cache_clear()`). This is unrelated to this feature. New test file added: `breathecode/payments/tests/urls/tests_academy_user_consumable.py` (no auth → 401; success path with mocks → 201 + invoice).
- **Optional**: Plan mentions optionally setting `standalone_invoice` in `build_consumables_from_bag` and `process_auto_recharge`; not implemented in this pass.
- **Docs**: Endpoint documented in `docs/llm-docs/BC_CHECKOUT_CONSUMABLE.md` (section "Academy staff: grant consumables to a user").
