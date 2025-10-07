# Auto-Recharge Architecture

Detailed architecture diagrams and technical implementation of the auto-recharge system.

## Component Architecture

### SubscriptionBillingTeam Model

**Fields:**
- `auto_recharge_enabled`: bool
- `recharge_threshold_amount`: decimal
- `recharge_amount`: decimal
- `max_period_spend`: decimal (optional)

**Methods:**
- `get_current_monthly_period_dates()` → (start, end)
- `get_current_period_spend()` → float
- `can_auto_recharge(amount, lang)` → (bool, str)

**Relationship:** Has many Consumables

### Consumable Model

**Fields:**
- `subscription_billing_team`: FK (nullable)
- `user`: FK (null for team consumables)
- `how_many`: int (-1 = unlimited)
- `service_item`: FK

**Relationship:** References AcademyService via service_item

### AcademyService Model

**Fields:**
- `academy`: FK
- `service`: FK
- `price_per_unit`: decimal

**Purpose:** Provides pricing for balance calculations

## Signal Flow

```
┌──────────────────┐
│   User Action    │
│  (Consume API)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  consume_service.send(instance=consumable, how_many=X)      │
└────────┬─────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────────────────────┐
         │                                                      │
         ▼                                                      ▼
┌─────────────────────────┐                    ┌──────────────────────────┐
│ consume_service_receiver│                    │ check_consumable_balance │
│  (Update how_many)      │                    │  _for_auto_recharge      │
└─────────────────────────┘                    └──────────┬───────────────┘
                                                          │
                                                          │ 1. Check team exists
                                                          │ 2. Check auto_recharge_enabled
                                                          │ 3. Check spending limit
                                                          │ 4. Calculate balance
                                                          │    (using AcademyService pricing)
                                                          │
                                                          ▼
                                               ┌──────────────────────┐
                                               │ Balance < threshold? │
                                               └──────────┬───────────┘
                                                          │ Yes
                                                          ▼
                                               ┌──────────────────────────┐
                                               │ consumable_balance_low   │
                                               │  .send(team, amount)     │
                                               └──────────┬───────────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────────┐
                                               │ trigger_auto_recharge    │
                                               │  _task receiver          │
                                               └──────────┬───────────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────────┐
                                               │ process_auto_recharge    │
                                               │  .delay(team_id, amount) │
                                               └──────────┬───────────────┘
                                                          │
                                                          ▼
                                                    [Celery Queue]
                                                          │
                                                          ▼
                                               ┌──────────────────────────┐
                                               │  Celery Worker           │
                                               │  + Redis Lock            │
                                               └──────────┬───────────────┘
                                                          │
                                                          ├─ Create consumables
                                                          ├─ Create invoice
                                                          └─ Send notification
```

## Decision Tree

```
                    ┌─────────────────────┐
                    │ Consumable consumed │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Has billing team?    │
                    └──────────┬───────────┘
                          Yes  │  No → END
                               ▼
                    ┌──────────────────────┐
                    │ Auto-recharge        │
                    │ enabled?             │
                    └──────────┬───────────┘
                          Yes  │  No → END
                               ▼
                    ┌──────────────────────┐
                    │ Monthly limit set?   │
                    └──────────┬───────────┘
                          Yes  │  No → Skip to balance check
                               ▼
                    ┌──────────────────────┐
                    │ Current ≥ limit?     │
                    └──────────┬───────────┘
                          Yes  │  No
                               │   │
                          END ←┘   │
                                   ▼
                    ┌──────────────────────┐
                    │ Calculate balance    │
                    │ (AcademyService      │
                    │  pricing)            │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Unlimited (-1)?      │
                    └──────────┬───────────┘
                          Yes  │  No
                               │   │
                          END ←┘   │
                                   ▼
                    ┌──────────────────────┐
                    │ Balance < threshold? │
                    └──────────┬───────────┘
                          Yes  │  No → END
                               ▼
                    ┌──────────────────────┐
                    │ Would exceed limit?  │
                    └──────────┬───────────┘
                          Yes  │  No
                               │   │
                    ┌──────────▼───▼───────┐
                    │ Adjust amount        │
                    │ (partial or full)    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Emit signal          │
                    │ → Trigger task       │
                    └──────────────────────┘
```

## Recharge Process (Celery Task)

**Steps:**

**0. Acquire Redis Lock**
- Key: `"auto_recharge:team:{team_id}"`
- Timeout: 300 seconds
- Blocking: False (fail fast if locked)

**1. Fetch Team**
- Get SubscriptionBillingTeam by ID
- Verify auto_recharge_enabled still true

**2. Validate Spending Limit**
- Get current_period_spend (from invoices)
- Check < max_period_spend
- Adjust recharge_amount if needed

**3. Find Service Items**
- Query team-allowed services from subscription
- Filter by is_team_allowed=True

**4. Create Consumables**
- For each service item:
  - Get AcademyService pricing
  - Calculate units (amount / price_per_unit)
  - Create Consumable(user=None, subscription_billing_team=team, how_many=units)
- Log creation

**5. Create Invoice (TODO)**
- Invoice.objects.create(user=subscription.user, amount=total_spent, subscription_billing_team=team)
- Spending tracked via invoices

**6. Send Notification**
- Email to subscription.user
- Include: amount, balance, limit, currency

**7. Release Lock & Return**
- lock.release()
- Return result dict

## Data Flow Example

### Initial State
```
Team ID: 123
Subscription Currency: USD
├─ auto_recharge_enabled: True
├─ recharge_threshold_amount: $10
├─ recharge_amount: $20
├─ max_period_spend: $100
├─ current_period_spend: $40 (from invoices)
└─ Team Consumables:
    ├─ Mentorship: 5 hours × $2/hour = $10
    └─ Events: 2 tickets × $1/ticket = $2
    Total Balance: $12
```

### User Consumes 5 Mentorship Hours
```
consume_service.send(consumable, how_many=5)

Balance Calculation:
  Before: 5 hours × $2 = $10
  After:  0 hours × $2 = $0
  Total:  $0 + $2 = $2

Check: $2 < $10 (threshold) ✓
Check: $40 + $20 = $60 < $100 (limit) ✓
→ Trigger recharge
```

### Recharge Process
```
process_auto_recharge.delay(team_id=123, recharge_amount=20)

1. Acquire lock: "auto_recharge:team:123"
2. Find services: Mentorship, Events
3. Distribute $20:
   - Mentorship: $10 → 5 hours
   - Events: $10 → 10 tickets
4. Create invoice: $20
5. Send email
6. Release lock
```

### Final State
```
Team ID: 123
├─ auto_recharge_enabled: True
├─ recharge_threshold_amount: $10
├─ recharge_amount: $20
├─ max_period_spend: $100
├─ current_period_spend: $60 ($40 + $20 from invoice)
└─ Team Consumables:
    ├─ Mentorship: 5 hours × $2/hour = $10
    └─ Events: 12 tickets × $1/ticket = $12
    Total Balance: $22
```

## Integration Points

### External Integrations

**Django Signals (Capy Core Emisors)**
- consume_service (trigger)
- consumable_balance_low (emit)

**Celery (Task Manager Plugin)**
- Task queue (RabbitMQ)
- Workers (process_auto_recharge)
- Priority: NOTIFICATION

**Redis**
- Distributed locks
- Key: `"auto_recharge:team:{id}"`

**Email Service (Notify Actions)**
- notify_actions.send_email_message()
- Template: "auto_recharge_completed"

**Payment Gateway (Stripe)**
- stripe.pay() method
- Creates Invoice model

**Database Models**
- SubscriptionBillingTeam (config)
- Consumable (balance)
- ServiceItem (team-allowed flag)
- AcademyService (pricing)
- Invoice (spending tracking)

## Error Handling

### Error Scenarios

**Lock Already Acquired**
- AbortTask("Auto-recharge already in progress")
- Log warning (safe to ignore)

**Team Not Found**
- AbortTask("Team {id} not found")
- Log error

**Auto-Recharge Disabled**
- AbortTask("Auto-recharge disabled")
- Log warning

**Period Limit Reached**
- AbortTask("Period spending limit reached")
- Log warning

**No Team Service Items**
- AbortTask("No team-allowed services")
- Log warning

**AcademyService Not Found**
- Skip service (continue with others)
- Log warning

**Notification Failure**
- Log warning (non-critical)
- Continue (task succeeds)

## Performance Considerations

### Signal Receiver Optimization
```python
# Lightweight check in receiver
def check_consumable_balance_for_auto_recharge(...):
    # Quick checks first (avoid DB queries if possible)
    if not instance.subscription_billing_team:
        return  # Fast exit

    team = instance.subscription_billing_team
    if not team.auto_recharge_enabled:
        return  # Fast exit

    # Only calculate balance if needed
    # Uses select_related() for efficiency
```

### Celery Task Optimization
```python
# Heavy processing in async task
@task(bind=True, priority=TaskPriority.NOTIFICATION)
def process_auto_recharge(...):
    # Redis lock prevents concurrent execution
    # select_related() reduces DB queries
    # Bulk operations where possible
```

### Database Queries
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse relations
- Aggregate queries for balance calculation
- Index on `subscription_billing_team` field

## Security Measures

**1. Owner-Only Modification**
- API endpoint validates `request.user == subscription.user`
- Admin requires staff permissions

**2. Spending Limits**
- `max_period_spend` prevents runaway costs
- Partial recharge when approaching limit

**3. Redis Lock**
- Prevents race conditions
- Timeout prevents stuck locks (5 min)

**4. Invoice Audit Trail**
- All recharges create invoices
- Spending calculated from invoices (not model fields)

**5. Input Validation**
- Serializer validates amounts (min_value=0)
- Decimal precision enforced
- Null handling for optional fields
