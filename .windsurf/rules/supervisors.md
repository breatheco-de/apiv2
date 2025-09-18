---
trigger: always_on
description:
globs:
---

# Supervisors

You are an expert in Python, Django, and supervisor development for the BreatheCode API.

Supervisors are a critical component of BreatheCode's production monitoring and data integrity system. They act as automated watchdogs that continuously monitor and maintain the health of critical business components, particularly those involving financial transactions, user plans, and other essential data.

## Purpose
- Production-level monitoring of critical system components
- Maintaining data integrity across complex operations
- Automated detection and resolution of inconsistencies
- Ensuring reliability of payment and subscription systems
- Preventing data corruption in high-value transactions

## Your expertise includes
- Creating and maintaining supervisors and issue handlers
- Understanding supervisor scheduling and execution
- Implementing self-healing mechanisms
- Monitoring system health
- Handling data inconsistencies


## Production Monitoring and Data Integrity

### Critical Components
1. Payment Systems
   - Monitor transaction completeness
   - Verify subscription state matches payment status
   - Detect and resolve payment processing issues
   - Ensure proper service activation after payment

2. User Plans and Benefits
   - Validate plan assignments
   - Monitor benefit allocation
   - Track service consumption
   - Detect unauthorized access attempts

3. Service Consumption
   - Track resource usage
   - Monitor quota compliance
   - Detect abuse patterns
   - Ensure fair service distribution

4. Data Consistency
   - Cross-reference related data points
   - Verify referential integrity
   - Detect orphaned or invalid records
   - Maintain audit trails

### Health Indicators
1. Transaction Integrity
   - Payment completion rates
   - Subscription activation success
   - Service delivery confirmation
   - Refund and cancellation processing

2. System Consistency
   - Data synchronization status
   - Cross-system validation results
   - Error rates and patterns
   - Recovery success metrics

3. User Experience
   - Service availability
   - Benefit activation times
   - Issue resolution speed
   - Customer impact metrics

### Response Mechanisms
1. Automated Fixes
   - Retry failed transactions
   - Resync inconsistent data
   - Restore missing benefits
   - Adjust incorrect quotas

2. Alert Thresholds
   - Critical issue notifications
   - Escalation triggers
   - Performance degradation warnings
   - Security incident alerts

3. Recovery Procedures
   - Transaction rollback/retry
   - Data reconciliation
   - Service reactivation
   - Customer compensation

### Best Practices for Production
1. Careful Delta Selection
   - High-value components need frequent checks
   - Balance thoroughness with system load
   - Consider business hours and peak times
   - Adjust based on historical patterns

2. Robust Error Handling
   - Never leave systems in inconsistent states
   - Log all fix attempts comprehensively
   - Implement safe rollback mechanisms
   - Consider downstream impacts

3. Performance Considerations
   - Optimize database queries
   - Use appropriate indexes
   - Implement caching where suitable
   - Monitor supervisor overhead

4. Security Awareness
   - Protect sensitive data in logs
   - Validate data before fixes
   - Monitor for abuse patterns
   - Maintain audit trails

## Key Principles
- Keep supervisors focused on detecting specific types of issues
- Make issue handlers idempotent (can be run multiple times safely)
- Use meaningful codes that clearly identify the type of issue
- Include all necessary parameters in supervisor yield statements
- Return appropriate values from issue handlers
- Set appropriate delta values based on urgency and frequency
- Document purpose and behavior of each supervisor and handler

## Implementation Details
- Supervisors and issues are stored in `breathecode.monitoring` models
- System tracks when supervisors last ran
- Records detected issues and fix attempts
- Automatically schedules based on delta parameter
- Triggers issue handlers when issues are detected

## Creating New Supervisors

1. Define supervisor function with `@supervisor` decorator:
```python
@supervisor(delta=timedelta(hours=1))
def check_something():
    # Detection logic here
    if issue_detected:
        yield {
            'code': 'fix-something',
            'message': 'Issue description',
            'params': {'param1': 'value1'}
        }
```

2. Define issue handler with `@issue` decorator:
```python
@issue(code='fix-something')
def fix_something(param1):
    # Fix logic here
    if fixed:
        return True  # Fixed
    elif can_retry:
        return None  # Will retry
    else:
        return False  # Unfixable
```

3. Match code in yield statement to handler function name
4. Ensure parameters match between supervisor and handler

## Benefits
1. Separation of Concerns
   - Supervisors focus on detection
   - Handlers focus on fixing

2. Automatic Healing
   - System detects and fixes issues
   - Reduces manual intervention

3. Monitoring
   - Issues recorded in database
   - Provides system health visibility

4. Retry Logic
   - Configurable retry attempts
   - Handles temporary failures

5. Scalability
   - Add new supervisors without code changes
   - Independent operation

## Common Use Cases
- Detecting stalled processes
- Resolving data inconsistencies
- Monitoring system resources
- Retrying failed operations
- Detecting security issues
- Validating payment and subscription states
- Ensuring plan benefits are correctly applied
- Monitoring service consumption and quotas
- Detecting anomalies in financial transactions
- Verifying data consistency between related systems

## Best Practices
1. Focus supervisors on specific issues
2. Make handlers idempotent
3. Use clear issue codes
4. Include necessary parameters
5. Return appropriate status
6. Set appropriate deltas
7. Document thoroughly

## Rules
1. Always make issue handlers idempotent
2. Use meaningful and specific issue codes
3. Include all required parameters in yield
4. Document purpose and behavior
5. Set appropriate delta values
6. Consider retry implications
7. Test both detection and fixing
8. Monitor fix success rates

## Example Implementation

```python
from datetime import timedelta
from django.utils import timezone
from breathecode.utils.decorators import supervisor, issue

@supervisor(delta=timedelta(minutes=10))
def supervise_pending_bags():
    """
    Supervisor to check for bags that are paid but not delivered.
    This helps identify issues in the subscription/plan financing creation process.
    """
    utc_now = timezone.now()

    # Filter bags that need attention
    pending_bags = Bag.objects.filter(
        status="PAID",
        was_delivered=False,
        updated_at__lte=utc_now - timedelta(minutes=30)
    )

    for bag in pending_bags:
        yield {
            'code': 'pending-bag-delivery',
            'message': f'Bag {bag.id} not delivered',
            'params': {'bag_id': bag.id}
        }

@issue(supervise_pending_bags, delta=timedelta(minutes=30), attempts=3)
def pending_bag_delivery(bag_id: int):
    """
    Issue handler for pending bag delivery.
    Attempts to retry the delivery process.
    """
    bag = Bag.objects.filter(
        id=bag_id,
        status="PAID",
        was_delivered=False
    ).first()

    if not bag:
        return True  # Already fixed

    res = retry_pending_bag(bag)

    if res == "done":
        return True  # Fixed
    elif res == "scheduled":
        return None  # Retry later
    else:
        return False  # Unfixable
```

## Models

### Supervisor
```python
class Supervisor(models.Model):
    task_module = models.CharField(max_length=200)
    task_name = models.CharField(max_length=200)
    delta = models.DurationField(
        default=timedelta(minutes=30),
        help_text="How long to wait for the next execution"
    )
    ran_at = models.DateTimeField(null=True, blank=True)
```

### SupervisorIssue
```python
class SupervisorIssue(models.Model):
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE)
    occurrences = models.PositiveIntegerField(default=1)
    attempts = models.PositiveIntegerField(default=0)
    code = models.SlugField(null=True, blank=True)
    params = models.JSONField(null=True, blank=True)
    fixed = models.BooleanField(null=True, blank=True)
    error = models.TextField(max_length=255)
    ran_at = models.DateTimeField(null=True, blank=True)
```

## Testing

1. Test supervisor detection:
```python
def test_supervisor_detection():
    # Create test conditions
    create_test_data()

    # Run supervisor
    issues = list(supervise_pending_bags())

    # Assert issues detected
    assert len(issues) == 1
    assert issues[0]['code'] == 'pending-bag-delivery'
```

2. Test issue handler:
```python
def test_issue_handler():
    # Create test issue
    bag = create_test_bag()

    # Run handler
    result = pending_bag_delivery(bag.id)

    # Assert fixed
    assert result is True
    assert bag.refresh_from_db().was_delivered
```

## Monitoring

1. Admin Interface
   - View all supervisors
   - Track issue occurrences
   - Monitor fix attempts
   - Review error messages

2. Management Command
   - Run supervisors manually
   - Force issue fixes
   - Clear old issues

3. Metrics
   - Issue detection rate
   - Fix success rate
   - Average fix time
   - Common issues
