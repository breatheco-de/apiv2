# Supervisors Documentation

## Overview

The **Supervisors** system in the `breathecode` Django application provides automated quality assurance by periodically monitoring the system for issues and triggering corrective actions. Supervisors are implemented as Python functions decorated with `@supervisor`, which run at specified intervals to detect issues (e.g., data inconsistencies). Detected issues are stored as `SupervisorIssue` objects and handled by functions decorated with `@issue`. The system uses Celery for asynchronous task execution and a Django management command to schedule supervisors and issue handlers.

This documentation covers the supervisors defined in `breathecode/payments/supervisors.py`, their triggering mechanism, and how to extend or maintain the system.

## Purpose

Supervisors ensure data integrity and compliance with business rules by:
- Identifying issues such as orphaned team members (active `TeamMember` objects without associated `Consumable` objects) or subscriptions exceeding team size limits.
- Creating `SupervisorIssue` records for detected problems.
- Triggering issue handlers to resolve problems (e.g., creating missing consumables or notifying users).
- Retrying failed resolutions with configurable attempts and delays.

## Components

### Models
- **`Supervisor` (in `breathecode.monitoring.models`)**:
  - Tracks metadata for each supervisor function.
  - Fields:
    - `task_module`: The Python module containing the supervisor (e.g., `breathecode.payments.supervisors`).
    - `task_name`: The supervisor function name (e.g., `supervise_orphaned_team_members`).
    - `delta`: The interval between runs (e.g., `timedelta(hours=2)`).
    - `ran_at`: The last execution time (`datetime`).
- **`SupervisorIssue` (in `breathecode.monitoring.models`)**:
  - Stores detected issues for processing by issue handlers.
  - Fields:
    - `supervisor`: Foreign key to the `Supervisor` instance.
    - `error`: The issue description (e.g., `Team member 123 (user@example.com) has no consumables`).
    - `code`: The issue handler code (e.g., `fix-orphaned-team-member`).
    - `params`: Parameters for the issue handler (e.g., `{'team_member_id': 123}`).
    - `ran_at`: When the issue was detected (`datetime`).
    - `occurrences`: Number of times the issue was detected.
    - `fixed`: When the issue was resolved (`datetime`, nullable).
    - `attempts`: Number of resolution attempts.

### Decorators
- **`@supervisor(delta, auto=True, raises=False)` (in `breathecode.utils.decorators`)**:
  - Registers a supervisor function to run periodically.
  - Parameters:
    - `delta`: Interval between runs (e.g., `timedelta(hours=2)`). Defaults to 1 hour if `None`.
    - `auto`: If `True`, automatically runs the supervisor (unused in provided code).
    - `raises`: If `True`, raises exceptions (unused in provided code).
  - Functionality:
    - Adds the supervisor to the global `paths` set as `(module, name, delta)`.
    - Creates or updates a `Supervisor` model instance.
    - Wraps the supervisor function to process yielded issues, creating `SupervisorIssue` objects.
    - Supports both synchronous and asynchronous supervisors (using `async_wrapper` for async generators).
- **`@issue(code, attempts, delta)`**:
  - Associates a function with an issue `code` for handling specific issues.
  - Parameters:
    - `code`: The issue identifier (e.g., `fix-orphaned-team-member`).
    - `attempts`: Maximum retry attempts (e.g., 3).
    - `delta`: Delay between retries (e.g., `timedelta(minutes=30)`).
  - Functionality:
    - Executes the handler with `params` from the `SupervisorIssue`.
    - Retries if the handler returns `None` or raises an exception, up to `attempts` times.

### Management Command
- **Command**: `python manage.py run_supervisors` (assumed name, located in `breathecode/monitoring/management/commands/run_supervisors.py`).
- **Functionality**:
  - Deletes `SupervisorIssue` objects older than 7 days.
  - Registers all supervisors from the `paths` set as `Supervisor` model instances.
  - Schedules supervisors that are due to run using `run_supervisor.delay(supervisor_id)`.
  - Schedules issue handlers for unresolved issues using `fix_issue.delay(issue_id)`.

### Celery Tasks
- **`run_supervisor` (in `breathecode.monitoring.tasks`)**:
  - Executes a supervisor function by `Supervisor` ID.
  - Updates `ran_at` to `timezone.now()`.
- **`fix_issue` (in `breathecode.monitoring.tasks`)**:
  - Calls the `@issue` handler for a `SupervisorIssue` based on its `code`.
  - Passes `params` to the handler.
  - Updates `attempts` and `fixed` fields.

## Supervisors in `breathecode/payments/supervisors.py`

### `supervise_orphaned_team_members`
- **Purpose**: Identifies active `TeamMember` objects without associated `Consumable` objects.
- **Interval**: Every 2 hours (`delta=timedelta(hours=2)`).
- **Logic**:
  - Queries `TeamMember` objects where:
    - `status=TeamMember.Status.ACTIVE`
    - `user` is not null
    - `joined_at` is not null
    - No `Consumable` exists for the `TeamMember`
  - Yields an issue for each orphaned member:
    ```python
    {
        'code': 'fix-orphaned-team-member',
        'message': f'Team member {member.id} ({member.email}) has no consumables',
        'params': {'team_member_id': member.id}
    }
    ```

### `supervise_team_member_limits`
- **Purpose**: Identifies `Subscription` objects with more active `TeamMember` objects than allowed by their `ServiceItem.max_team_members`.
- **Interval**: Every 6 hours (`delta=timedelta(hours=6)`).
- **Logic**:
  - Queries `ServiceItem` objects with `is_team_allowed=True`.
  - For each `ServiceItem`, finds `Subscription` objects where the count of active `TeamMember` objects (via `Consumable`) exceeds `max_team_members`.
  - Yields an issue for each violation:
    ```python
    {
        'code': 'fix-team-size-exceeded',
        'message': f'Subscription {subscription.id} has {subscription.active_team_count} team members, max allowed: {service_item.max_team_members}',
        'params': {
            'subscription_id': subscription.id,
            'service_item_id': service_item.id,
            'current_count': subscription.active_team_count,
            'max_allowed': service_item.max_team_members
        }
    }
    ```

## Issue Handlers

### `fix_orphaned_team_member(team_member_id: int)`
- **Code**: `fix-orphaned-team-member`
- **Attempts**: 3
- **Retry Delay**: 30 minutes (`timedelta(minutes=30)`)
- **Logic**:
  - Checks if the `TeamMember` exists and is active.
  - If consumables already exist, marks as resolved.
  - Calls `create_team_member_consumables(team_member)` to create missing consumables.
  - Returns `True` if resolved, `None` to retry on error.
- **Logging**:
  - Success: `logger.info(f"Fixed orphaned team member {team_member_id}")`
  - Failure: `logger.error(f"Failed to fix orphaned team member {team_member_id}: {e}")`

### `fix_team_size_exceeded(subscription_id: int, service_item_id: int, current_count: int, max_allowed: int)`
- **Code**: `fix-team-size-exceeded`
- **Attempts**: 2
- **Retry Delay**: 1 hour (`timedelta(hours=1)`)
- **Logic**:
  - Checks if the `Subscription` and `ServiceItem` exist.
  - Sends an email notification to the subscription owner using `send_email_message`.
  - Returns `True` if the notification is sent, `None` to retry on error.
- **Logging**:
  - Success: `logger.warning(f"Notified user about team size exceeded: subscription {subscription_id}")`
  - Failure: `logger.error(f"Failed to handle team size exceeded for subscription {subscription_id}: {e}")`

## Triggering Mechanism

Supervisors are triggered via the `run_supervisors` management command, which is typically run periodically (e.g., via a cron job or Celery Beat). The process is as follows:

1. **Command Execution**:
   - Run `python manage.py run_supervisors`.
   - Deletes `SupervisorIssue` objects older than 7 days.
   - Registers all supervisors from the `paths` set as `Supervisor` model instances.
   - Calls `run_supervisors()` and `fix_issues()`.

2. **Supervisor Scheduling**:
   - `run_supervisors` queries all `Supervisor` objects.
   - For each supervisor, checks if it’s due to run (`ran_at is None` or `now - delta > ran_at`).
   - Schedules eligible supervisors via `run_supervisor.delay(supervisor_id)` (a Celery task).
   - Logs: `Supervisor breathecode.payments.supervisors.supervise_orphaned_team_members scheduled`.

3. **Supervisor Execution**:
   - The `run_supervisor` task:
     - Retrieves the `Supervisor` by ID.
     - Imports and runs the supervisor function (e.g., `supervise_orphaned_team_members`).
     - Updates `ran_at = timezone.now()`.
   - The supervisor yields issue dictionaries, which the `@supervisor` decorator’s `wrapper` converts to `SupervisorIssue` objects:
     - `supervisor`: Links to the `Supervisor` instance.
     - `error`: Issue message.
     - `code`: Issue handler code.
     - `params`: Parameters for the handler.
     - `ran_at`: Detection time.
     - `occurrences`: Incremented for recurring issues.

4. **Issue Handling**:
   - `fix_issues` queries `SupervisorIssue` objects where `fixed=None` and `attempts < 3`.
   - Schedules `fix_issue.delay(issue_id)` for each issue.
   - The `fix_issue` task:
     - Retrieves the `SupervisorIssue`.
     - Calls the `@issue` handler based on the `code` (e.g., `fix_orphaned_team_member`).
     - Updates `attempts` and `fixed` if resolved.
     - Retries if `None` is returned, up to the handler’s `attempts` limit.

5. **Scheduling**:
   - The command should be run periodically (e.g., every 5 minutes via cron or Celery Beat):
     ```bash
     */5 * * * * python manage.py run_supervisors
     ```
   - This ensures supervisors run at their specified intervals (2 hours for `supervise_orphaned_team_members`, 6 hours for `supervise_team_member_limits`).

## Example Flow
1. **9:00 AM**: Run `python manage.py run_supervisors`.
   - Deletes old issues.
   - Registers supervisors in `Supervisor`.
   - Schedules `supervise_orphaned_team_members` (due immediately).
2. **run_supervisor Task**:
   - Runs `supervise_orphaned_team_members`, finds `TeamMember` ID 123 without consumables.
   - Creates a `SupervisorIssue` with `code='fix-orphaned-team-member'`, `params={'team_member_id': 123}`.
3. **fix_issues**:
   - Schedules `fix_issue.delay(issue_id)` for the issue.
   - `fix_orphaned_team_member` creates consumables and marks the issue as resolved.
4. **11:00 AM**: Next run checks if `supervise_orphaned_team_members` is due again.

## Best Practices
- **Idempotency**: Ensure issue handlers (e.g., `create_team_member_consumables`) are idempotent to avoid duplicate actions.
- **Performance**:
  - Add indexes to optimize queries:
    ```python
    class TeamMember(models.Model):
        status = models.CharField(max_length=20, choices=TeamMember.Status.choices)
        user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
        joined_at = models.DateTimeField()
        class Meta:
            indexes = [
                models.Index(fields=['status', 'user', 'joined_at']),
            ]
    ```
    ```python
    class Consumable(models.Model):
        team_member = models.ForeignKey('TeamMember', on_delete=models.CASCADE, null=True)
        service_item = models.ForeignKey('ServiceItem', on_delete=models.CASCADE)
        class Meta:
            indexes = [
                models.Index(fields=['team_member']),
            ]
    ```
  - Batch `SupervisorIssue` creation for large datasets:
    ```python
    issues = [
        SupervisorIssue(
            supervisor=instance,
            error=f'Team member {member.id} ({member.email}) has no consumables',
            code='fix-orphaned-team-member',
            params={'team_member_id': member.id},
            ran_at=timezone.now()
        )
        for member in orphaned_members
    ]
    SupervisorIssue.objects.bulk_create(issues)
    ```
- **Monitoring**: Add metrics (e.g., via `statsd`) to track supervisor runs and issue resolutions.
- **Retry Consistency**: Align `fix_issues` retry limit with `@issue` `attempts` (e.g., `fix_team_size_exceeded` has `attempts=2`, but `fix_issues` assumes 3).

## Troubleshooting
- **Supervisor Not Running**: Check if the command is scheduled (e.g., via cron or Celery Beat) and if Celery workers are active.
- **Issues Not Resolved**: Verify `fix_issue` task is running and the `@issue` handler’s `code` matches the `SupervisorIssue.code`.
- **Performance Issues**: Profile queries and add indexes as needed.
- **Logging**: Check logs (`logger.info`, `logger.error`) for errors in `fix_orphaned_team_member` or `fix_team_size_exceeded`.

## Extending the System
To add a new supervisor:
1. Define the supervisor function in `breathecode/payments/supervisors.py`:
   ```python
   @supervisor(delta=timedelta(hours=4))
   def supervise_new_condition():
       for item in SomeModel.objects.filter(some_condition=True):
           yield {
               'code': 'fix-new-condition',
               'message': f'Issue with {item.id}',
               'params': {'item_id': item.id}
           }
   ```
2. Define the issue handler:
   ```python
   @issue(code='fix-new-condition', attempts=3, delta=timedelta(minutes=30))
   def fix_new_condition(item_id: int):
       try:
           item = SomeModel.objects.get(id=item_id)
           # Fix logic
           logger.info(f"Fixed item {item_id}")
           return True
       except Exception as e:
           logger.error(f"Failed to fix item {item_id}: {e}")
           return None
   ```
3. Ensure the management command is run periodically.
