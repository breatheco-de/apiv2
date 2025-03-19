# Supervisor

## Overview

The `@supervisor` and `@issue` decorators are part of a monitoring system that helps identify and automatically fix issues in the application. They work together to create a self-healing mechanism where:

1. `@supervisor` functions detect potential issues in the system
2. `@issue` handlers attempt to fix those issues automatically

## @supervisor Decorator

### Purpose

The `@supervisor` decorator is used to create monitoring functions that periodically check for potential issues or anomalies in the system. These functions yield messages when they detect problems, which are then recorded in the database.

### Syntax

```python
@supervisor(delta=timedelta(hours=6))
def supervise_something():
    # Check for issues
    if issue_detected:
        # Simple message
        yield "Something is wrong"

        # Or with code and parameters for issue handlers
        yield "Specific issue description", "issue-code", {"param1": value1, "param2": value2}
```

### Parameters

- `delta`: A `timedelta` object that specifies how often the supervisor should run. For example, `delta=timedelta(hours=6)` means the supervisor will run every 6 hours.
- `auto`: Boolean that determines if the supervisor should run automatically (default is `True`).
- `raises`: Boolean that determines if the supervisor should raise exceptions (default is `False`).

### Return Value

A supervisor function should be a generator that yields:

- A simple string message describing the issue, or
- A tuple containing: 1. A string message, 2. An issue code, 3. A dictionary of parameters for the issue handler

### Example

```python
@supervisor(delta=timedelta(minutes=10))
def supervise_pending_bags_to_be_delivered():
    """
    Supervisor to check for bags that are paid but not delivered.
    This helps identify issues in the subscription/plan financing creation process.
    """
    utc_now = timezone.now()

    # Filter bags that are paid but not delivered, updated between 5 and 30 minutes ago
    pending_bags = Bag.objects.filter(
        status="PAID",
        was_delivered=False,
        updated_at__lte=utc_now - timedelta(minutes=30),
        updated_at__gte=utc_now - timedelta(minutes=5),
    )

    for bag in pending_bags:
        invoice = bag.invoices.filter(status="FULFILLED").order_by("-paid_at").first()
        if invoice:
            yield (
                f"Bag {bag.id} for user {bag.user.email} in academy {bag.academy.name} has not been delivered",
                "pending-bag-delivery",
                {"bag_id": bag.id},
            )
```

## @issue Decorator

### Purpose

The `@issue` decorator creates handler functions that attempt to fix issues detected by supervisors. When a supervisor yields an issue with a specific code, the corresponding issue handler is triggered to fix the problem.

### Syntax

```python
@issue(supervisor_function, delta=timedelta(minutes=30), attempts=3)
def fix_specific_issue(param1, param2):
    # Attempt to fix the issue
    if issue_fixed:
        return True  # Issue is fixed
    elif issue_cannot_be_fixed:
        return False  # Issue cannot be fixed
    else:
        return None  # Issue is not yet fixed, will retry later
```

### Parameters

- `supervisor_function`: The supervisor function that this issue handler is associated with.
- `delta`: A `timedelta` object that specifies how often the issue handler should retry if the issue is not fixed.
- `attempts`: The maximum number of attempts to fix the issue before giving up.

### Parameters Passed to the Handler

The parameters passed to the issue handler function come from the third element of the tuple yielded by the supervisor function. These parameters should match the parameter names in the issue handler function signature.

### Return Value

An issue handler function should return:

- `True`: The issue is fixed
- `False`: The issue cannot be fixed (will not retry)
- `None`: The issue is not yet fixed (will retry later, up to the specified number of attempts)

### Example

```python
@issue(supervise_pending_bags_to_be_delivered, delta=timedelta(minutes=30), attempts=3)
def pending_bag_delivery(bag_id: int):
    """
    Issue handler for pending bag delivery.
    This function is called when a bag is detected as paid but not delivered.
    It will attempt to retry the delivery process.
    """
    # Check if the bag still needs to be processed
    bag = Bag.objects.filter(id=bag_id, status="PAID", was_delivered=False).first()
    if not bag:
        # Bag was already delivered or doesn't exist, mark as fixed
        return True

    # Call the function to retry the delivery
    res = retry_pending_bag(bag)

    # Return True if the issue is fixed
    if res in ["scheduled", "done"]:
        return True

    # Return None to retry later
    return None
```

## How They Work Together

1. The `@supervisor` function runs periodically (based on its `delta` parameter) and checks for issues.
2. When an issue is detected, the supervisor yields a message, code, and parameters.
3. The system records this issue in the database.
4. The `@issue` handler associated with the supervisor (matching the yielded code) is triggered.
5. The issue handler receives the parameters yielded by the supervisor and attempts to fix the issue.
6. If the issue handler returns `None`, it will be retried later (based on the handler's `delta` parameter).
7. If the issue handler returns `True`, the issue is marked as fixed.
8. If the issue handler returns `False`, the issue is marked as unfixable.

## Benefits

1. **Separation of Concerns**: Supervisors focus on detecting issues, while issue handlers focus on fixing them.
2. **Automatic Healing**: The system can automatically detect and fix common issues without manual intervention.
3. **Monitoring**: Issues are recorded in the database, providing visibility into system health.
4. **Retry Logic**: Issue handlers can retry fixing issues multiple times with configurable delays.
5. **Scalability**: New supervisors and issue handlers can be added without modifying existing code.

## Best Practices

1. Keep supervisors focused on detecting specific types of issues.
2. Make issue handlers idempotent (can be run multiple times safely).
3. Use meaningful codes that clearly identify the type of issue.
4. Include all necessary parameters in the supervisor's yield statement.
5. Return appropriate values from issue handlers to indicate the status of the fix.
6. Set appropriate `delta` values based on the urgency and frequency of the issue.
7. Document the purpose and behavior of each supervisor and issue handler.

## Implementation Details

The supervisors and issues are stored in the database using the `Supervisor` and `SupervisorIssue` models from the `breathecode.monitoring` app. These models track:

- When supervisors last ran
- What issues were detected
- Whether issues have been fixed
- How many times an issue has occurred

The system automatically schedules supervisors to run based on their `delta` parameter and triggers issue handlers when issues are detected.

## Creating New Supervisors and Issue Handlers

To create a new supervisor and issue handler:

1. Define a supervisor function decorated with `@supervisor` that yields issues.
2. Define an issue handler function decorated with `@issue` that fixes the issues.
3. Make sure the code in the supervisor's yield statement matches the name of the issue handler function (with hyphens instead of underscores).
4. Ensure the parameters in the supervisor's yield statement match the parameters expected by the issue handler.

## Example Use Cases

- Detecting and fixing stalled processes
- Identifying and resolving data inconsistencies
- Monitoring system resources and taking action when thresholds are exceeded
- Checking for failed operations and retrying them
- Detecting security issues and taking remedial action

This monitoring and self-healing system helps maintain the health of the application by automatically detecting and fixing common issues, reducing the need for manual intervention and improving overall system reliability.
