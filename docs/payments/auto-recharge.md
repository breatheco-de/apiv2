# Auto-Recharge System

The auto-recharge system automatically replenishes team consumables when the balance runs low, ensuring uninterrupted service access.

## Overview

When a billing team's consumable balance falls below a configured threshold, the system automatically:

1. Purchases new consumables
2. Charges the subscription owner
3. Sends a notification
4. Respects monthly spending limits

## Key Features

### Configurable Thresholds
- **Recharge Threshold**: Balance level that triggers recharge (e.g., $10)
- **Recharge Amount**: How much to add when triggered (e.g., $20)
- **Monthly Limit**: Optional spending cap per period (e.g., $100/month)

### Real-Time Monitoring
- Monitors every consumable consumption via Django signals
- Calculates team balance in subscription currency
- Uses `AcademyService` pricing for accurate valuation

### Spending Control
- Tracks spending per monthly period (based on `subscription.paid_at`)
- Automatically resets each period
- Supports partial recharge to stay within limits

### Async Processing
- Uses Celery tasks for non-blocking operation
- Redis lock prevents concurrent recharges
- Email notifications to subscription owner

## Quick Start

### Enable Auto-Recharge

**Via API:**
```http
PUT /v2/payments/subscription/123/billing-team
Content-Type: application/json

{
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_period_spend": "100.00"
}
```

**Via Python:**
```python
from breathecode.payments.models import SubscriptionBillingTeam

team = SubscriptionBillingTeam.objects.get(subscription_id=123)
team.auto_recharge_enabled = True
team.recharge_threshold_amount = 10.00  # In subscription currency
team.recharge_amount = 20.00
team.max_period_spend = 100.00  # Optional
team.save()
```

### Check Current Status

```http
GET /v2/payments/subscription/123/billing-team
```

**Response:**
```json
{
  "id": 1,
  "auto_recharge_enabled": true,
  "recharge_threshold_amount": "10.00",
  "recharge_amount": "20.00",
  "max_period_spend": "100.00",
  "current_period_spend": 45.00,
  "period_start": "2025-01-15T00:00:00Z",
  "period_end": "2025-02-15T00:00:00Z",
  "currency": "USD"
}
```

## How It Works

### Flow Diagram

**Step-by-step process:**

1. **User consumes service**
2. **consume_service signal emitted**
3. **check_consumable_balance_for_auto_recharge**
4. **Calculate team balance** (in subscription currency)
5. **Balance < threshold?**
   - No → End
   - Yes → Continue
6. **Check monthly spending limit**
7. **Within limit?**
   - No → Log warning, End
   - Yes → Continue
8. **Emit consumable_balance_low signal**
9. **trigger_auto_recharge_task**
10. **Schedule process_auto_recharge.delay()**
11. **Celery Task with Redis Lock**
    - Create team consumables
    - Track spending via invoices
    - Send notification

### Example Scenario

**Initial State:**
```
Team Balance: $12 (in USD)
Threshold: $10
Recharge Amount: $20
Monthly Limit: $100
Current Period Spend: $40
```

**User Consumes Service:**
```
1. User consumes 5 mentorship hours
2. Balance: $12 → $7
3. $7 < $10 (threshold) ✓
4. $40 + $20 = $60 < $100 (limit) ✓
5. Trigger auto-recharge
```

**Recharge Process:**
```
1. Acquire Redis lock (prevent concurrent recharges)
2. Create consumables worth $20
3. Create invoice for $20
4. Send email to owner
5. Release lock
```

**Final State:**
```
Team Balance: $27 ($7 + $20)
Current Period Spend: $60 ($40 + $20)
```

## Configuration

### Model Fields

**SubscriptionBillingTeam:**
```python
auto_recharge_enabled = BooleanField(default=False)
recharge_threshold_amount = DecimalField(default=10.00)
recharge_amount = DecimalField(default=20.00)
max_period_spend = DecimalField(null=True, blank=True)
```

### Currency Handling

All amounts are in the **subscription's currency**:
```python
subscription = team.subscription
currency = subscription.currency  # e.g., Currency(code='USD')

# Balance calculated using AcademyService pricing
academy_service = AcademyService.objects.get(
    academy=subscription.academy,
    service=consumable.service_item.service
)
balance_amount += consumable.how_many * academy_service.price_per_unit
```

### Monthly Period Calculation

Spending periods are **monthly** from `subscription.paid_at` day:
```python
# Example: paid_at = Jan 15
# Periods: Jan 15-Feb 15, Feb 15-Mar 15, Mar 15-Apr 15, etc.

period_start, period_end = team.get_current_monthly_period_dates()
current_spend = team.get_current_period_spend()
```

## Advanced Topics

### Partial Recharge

When recharge would exceed monthly limit, the system performs a partial recharge:

```python
available_budget = max_period_spend - current_period_spend
if recharge_amount > available_budget:
    # Partial recharge
    actual_recharge = available_budget
else:
    # Full recharge
    actual_recharge = recharge_amount
```

### Unlimited Consumables

Consumables with `how_many=-1` (unlimited) don't trigger auto-recharge:

```python
if consumable.how_many == -1:
    balance_amount = -1  # Unlimited
    return  # Skip auto-recharge check
```

### Race Condition Prevention

Redis lock ensures only one recharge happens at a time:

```python
lock_key = f"auto_recharge:team:{team_id}"
lock = redis_client.lock(lock_key, timeout=300)

if not lock.acquire(blocking=False):
    raise AbortTask("Auto-recharge already in progress")

try:
    # Process recharge
finally:
    lock.release()
```

### Spending Tracking

Spending is tracked via invoices, not model fields:

```python
# Get spending from invoices (not a model field)
def get_current_period_spend(self) -> float:
    period_start, period_end = self.get_current_monthly_period_dates()

    invoices = Invoice.objects.filter(
        user=subscription.user,
        status=Invoice.Status.PAID,
        created_at__gte=period_start,
        created_at__lt=period_end
    )

    return float(invoices.aggregate(total=Sum("amount"))["total"] or 0)
```

## Troubleshooting

### Auto-Recharge Not Triggering

**Check:**

1. `auto_recharge_enabled = True`
2. Balance actually below threshold
3. Monthly limit not exceeded
4. Celery workers running
5. Redis available

**Debug:**
```python
team = SubscriptionBillingTeam.objects.get(id=123)
print(f"Enabled: {team.auto_recharge_enabled}")
print(f"Balance: {team.get_team_balance()}")
print(f"Threshold: {team.recharge_threshold_amount}")
print(f"Period Spend: {team.get_current_period_spend()}")
print(f"Period Limit: {team.max_period_spend}")
```

### Monthly Limit Reached

**Error:** "Billing period spending limit reached"

**Solution:**

- Wait for next billing period
- Increase `max_period_spend`
- Manually add consumables

### Concurrent Recharge Attempts

**Error:** "Auto-recharge already in progress"

**Cause:** Multiple consumptions triggered recharge simultaneously

**Solution:** Redis lock handles this automatically - one succeeds, others abort safely

## Testing

### Unit Tests

```bash
poetry run pytest breathecode/payments/tests/ --nomigrations -k auto_recharge
```

### Manual Testing

```python
# 1. Enable auto-recharge
team.auto_recharge_enabled = True
team.recharge_threshold_amount = 10.00
team.save()

# 2. Consume services until balance < threshold
# 3. Check Celery logs for task execution
# 4. Verify new consumables created
# 5. Check invoice created
```

## Related Documentation

- [Subscription Seats Guide](subscription-seats-guide.md) - Overview of team features
- [API Documentation](subscription-seats-api.md) - API endpoints
- [Architecture Diagrams](auto-recharge-architecture.md) - Detailed diagrams

## Migration Notes

### From Old Field Names

If migrating from older versions:

```python
# Old (deprecated)
recharge_threshold_dollars → recharge_threshold_amount
recharge_amount_dollars → recharge_amount
max_monthly_spend_dollars → max_period_spend
current_month_spend_dollars → (removed, calculated from invoices)
last_recharge_reset_at → (removed, not needed)
```

### Database Migration

```bash
poetry run python manage.py makemigrations payments
poetry run python manage.py migrate payments
```

## Security Considerations

1. **Owner-Only Access**: Only subscription owner can modify auto-recharge settings
2. **Spending Limits**: Mandatory for production to prevent abuse
3. **Redis Lock**: Prevents race conditions and double-charging
4. **Invoice Tracking**: All recharges create invoices for audit trail
5. **Validation**: Amount limits enforced at serializer level

## Performance Notes

- **Signal receivers** are lightweight (quick balance check)
- **Heavy processing** done in Celery task (async)
- **Redis lock timeout**: 5 minutes max
- **Balance calculation** optimized with `select_related()`
