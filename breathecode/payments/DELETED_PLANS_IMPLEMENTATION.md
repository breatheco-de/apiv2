# DELETED Plans Implementation

## Overview

This document describes the changes made to handle `DELETED` plans the same way as `DISCONTINUED` plans, ensuring users are not charged and consumables are never restocked for deleted plans.

## Changes Made

All changes were made to `/breathecode/payments/tasks.py`

### 1. `charge_subscription` Task (Line ~488)

**Change**: Updated to check for both DISCONTINUED and DELETED plans

```python
# Before:
elif subscription.plans.filter(status=Plan.Status.DISCONTINUED).exists():

# After:
elif subscription.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
```

**Effect**: 
- When a subscription contains a DELETED plan, it will be marked as DEPRECATED
- User receives notification email
- Charging is aborted
- Suggested alternative plans are shown (if PlanOffer exists)

### 2. `charge_plan_financing` Task (Line ~786)

**Change**: Added check for DELETED/DISCONTINUED plans after getting user settings

```python
# Check if plan financing has deleted or discontinued plans
if plan_financing.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
    plan_financing.status = PlanFinancing.Status.DEPRECATED
    plan_financing.save()
    
    # Send notification to user with optional suggested plan
    # ... (email notification code)
    
    raise AbortTask(f"PlanFinancing with id {plan_financing.id} has deleted/discontinued plans")
```

**Effect**:
- When a plan financing contains a DELETED plan, it will be marked as DEPRECATED
- User receives notification email
- Charging is aborted
- Suggested alternative plans are shown (if PlanOffer exists)

### 3. `renew_subscription_consumables` Task (Line ~280)

**Change**: Added check for DELETED/DISCONTINUED plans before renewing consumables

```python
# Check if subscription has deleted or discontinued plans
if subscription.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
    subscription.status = Subscription.Status.DEPRECATED
    subscription.save()
    raise AbortTask(
        f"The subscription {subscription.id} has deleted/discontinued plans, "
        "marked as deprecated, consumables will not be renewed"
    )
```

**Effect**:
- Prevents consumable restocking for subscriptions with DELETED plans
- Marks subscription as DEPRECATED
- Aborts the renewal process

### 4. `renew_plan_financing_consumables` Task (Line ~331)

**Change**: Added check for DELETED/DISCONTINUED plans before renewing consumables

```python
# Check if plan financing has deleted or discontinued plans
if plan_financing.plans.filter(status__in=[Plan.Status.DISCONTINUED, Plan.Status.DELETED]).exists():
    plan_financing.status = PlanFinancing.Status.DEPRECATED
    plan_financing.save()
    raise AbortTask(
        f"The plan financing {plan_financing.id} has deleted/discontinued plans, "
        "marked as deprecated, consumables will not be renewed"
    )
```

**Effect**:
- Prevents consumable restocking for plan financings with DELETED plans
- Marks plan financing as DEPRECATED
- Aborts the renewal process

## What This Accomplishes

### ✅ Prevents Charging
When a plan is DELETED:
- Subscriptions with the plan will NOT be charged
- Plan financings with the plan will NOT be charged
- Status automatically changes to DEPRECATED
- AbortTask prevents any payment processing

### ✅ Prevents Consumable Restocking
When a plan is DELETED:
- Consumables are NEVER restocked
- Renewal tasks are aborted immediately
- Users lose access when consumables run out

### ✅ User Notifications
When a subscription/financing is affected by a DELETED plan:
- User receives an email notification
- Email explains the discontinuation
- If a PlanOffer exists, user is directed to suggested alternative plan
- Email includes a link to checkout the suggested plan

### ✅ Data Integrity
- Subscriptions/financings are marked as DEPRECATED (not deleted)
- Historical data is preserved
- Audit trail is maintained
- Status changes are logged

## Testing Recommendations

1. **Test Subscription Charging**:
   - Create a subscription with an active plan
   - Delete the plan (set status to DELETED)
   - Trigger charge_subscription task
   - Verify: subscription marked as DEPRECATED, no charge made, email sent

2. **Test Plan Financing Charging**:
   - Create a plan financing with an active plan
   - Delete the plan (set status to DELETED)
   - Trigger charge_plan_financing task
   - Verify: financing marked as DEPRECATED, no charge made, email sent

3. **Test Consumable Renewal (Subscription)**:
   - Create subscription with consumables
   - Delete the plan
   - Trigger renew_subscription_consumables task
   - Verify: consumables NOT renewed, subscription marked as DEPRECATED

4. **Test Consumable Renewal (Plan Financing)**:
   - Create plan financing with consumables
   - Delete the plan
   - Trigger renew_plan_financing_consumables task
   - Verify: consumables NOT renewed, financing marked as DEPRECATED

5. **Test PlanOffer Integration**:
   - Create a DELETED plan with a PlanOffer pointing to an alternative
   - Trigger deprecation workflow
   - Verify: email contains link to suggested plan

## Edge Cases Handled

1. **Plan with no PlanOffer**: Email sent without suggested alternative
2. **Multiple plans in subscription**: If ANY plan is DELETED, entire subscription is deprecated
3. **Already DEPRECATED**: Won't trigger duplicate emails (checked in status conditions)
4. **Expired subscriptions**: Already handled by existing expiry checks
5. **Cancelled subscriptions**: Skipped by no_charge_statuses checks

## Related Models

- `Plan` - Contains status field (DELETED, DISCONTINUED, etc.)
- `Subscription` - Inherits from AbstractIOweYou, has plans M2M
- `PlanFinancing` - Inherits from AbstractIOweYou, has plans M2M
- `PlanOffer` - Links original_plan to suggested_plan
- `Consumable` - Units restocked by renewal tasks
- `ServiceStockScheduler` - Manages consumable renewal schedules

## Related Files

- `/breathecode/payments/models.py` - Model definitions
- `/breathecode/payments/tasks.py` - Modified file (all changes)
- `/breathecode/payments/views.py` - Plan deletion endpoint (sets status to DELETED)
- `/breathecode/payments/actions.py` - Helper functions
- `/breathecode/notify/actions.py` - Email sending functionality

## Migration Notes

No database migrations are required. All changes are to business logic only.

## Rollback Procedure

If issues arise, revert the changes in `/breathecode/payments/tasks.py` by:
1. Removing DELETED from status checks (revert to only DISCONTINUED)
2. Removing the new check blocks in renew_subscription_consumables and renew_plan_financing_consumables
3. Removing the new notification block in charge_plan_financing

## Future Enhancements

1. Add management command to bulk-deprecate subscriptions/financings for already-DELETED plans
2. Add supervisor to monitor and alert on orphaned subscriptions with DELETED plans
3. Add analytics tracking for plan deletion impact
4. Consider grace period before marking as DEPRECATED
5. Add admin action to "transfer" users from DELETED plan to suggested plan automatically

