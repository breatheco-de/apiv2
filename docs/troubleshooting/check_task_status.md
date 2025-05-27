# Task Status Diagnostic Tool

This document explains the `check_task_status` management command, which helps diagnose issues with tasks that appear stuck in Celery Task Manager.

## Overview

The command was created to investigate issue [#8696](https://github.com/breatheco-de/breatheco-de/issues/8696), where tasks appear as PENDING/SCHEDULED in the Django admin interface even though they may have been processed.

## Features

1. Identifies tasks stuck in SCHEDULED status for extended periods
2. Examines sample tasks for detailed investigation
3. Verifies actual execution status by checking:
   - Celery task state via AsyncResult
   - Downstream effects of specific task types
4. Checks for tasks stuck in other non-terminal states
5. Generates recommendations based on findings
6. Can save complete diagnostic output to a log file

## Command Arguments

| Argument            | Type   | Default | Description                                             |
| ------------------- | ------ | ------- | ------------------------------------------------------- |
| `--hours`           | int    | 906     | Number of hours to look back for stuck tasks            |
| `--check-execution` | flag   | False   | Enables verification of actual task execution           |
| `--limit`           | int    | 5       | Maximum number of sample tasks to analyze per task type |
| `--log-file`        | string | None    | Path where to save the diagnostic log file              |

## How to Run

Basic usage:

```bash
python manage.py check_task_status
```

With all options:

```bash
python manage.py check_task_status --hours=24 --check-execution --limit=10 --log-file=/path/to/task_diagnosis.log
```

## Output Details

The command outputs:

1. Summary of stuck tasks grouped by task module and name
2. Task counts and maximum duration they've been stuck
3. Sample of specific task instances with their:
   - ID, arguments, last run timestamp
   - Task ID for Celery correlation
   - Status message and attempt count
4. When `--check-execution` is used:
   - Celery task state from AsyncResult
   - Task-specific execution verification
   - Evidence of downstream effects
5. Tasks stuck in non-terminal states
6. Recommendations for resolution

## Example Output

```
Analyzing tasks stuck for more than 906 hours:
================================================================================

Task: task_manager.django.tasks.execute_signal
Count: 66597
Max Hours Stuck: 906.60

Sample Tasks:
ID: 12345678
Arguments: {"instance_id": 98765, "model_path": "breathecode.assignments.Task", "action": "status_updated"}
Last Run: 2025-02-15 10:23:45+00:00
Task ID: 87d6f3a5-c612-49b3-9fe1-23456789abcd
Status Message: None
Attempts: 2
----------------------------------------

Task: breathecode.notify.tasks.async_deliver_hook
Count: 63090
Max Hours Stuck: 906.50

Sample Tasks:
ID: 23456789
Arguments: {"hook_id": 12345, "retry": false}
Last Run: 2025-02-16 08:45:12+00:00
Task ID: 9e45f2a6-d723-48c4-8fd2-34567890bcde
Status Message: None
Attempts: 3
----------------------------------------

Other potentially stuck tasks by status:
================================================================================

Status: PENDING
Count: 1234

Recommendations:
================================================================================

1. Check Celery workers are running and processing tasks
2. Verify Redis connection and queue status
3. Look for any error patterns in the sample tasks
4. Consider resetting stuck tasks or investigating specific task modules
5. Check if the task_manager and actual task function are properly communicating status updates
6. For tasks with successful Celery execution but pending TaskManager status, update the TaskManager database
```

## Task-Specific Verification

The command checks specific task types:

1. `breathecode.assignments.tasks.async_learnpack_webhook`:

   - Verifies if webhook status was updated in database

2. `breathecode.notify.tasks.async_deliver_hook`:
   - Checks if hook delivery completed successfully

## Interpreting Results

### Possible Issues

1. **Task Execution Issues**: Tasks are not being processed by Celery

   - Celery workers may not be running
   - Redis message broker might be disconnected or data lost

2. **Status Update Issues**: Tasks are executed but status not updated
   - Database connection issues when updating status
   - Task execution errors preventing status update
   - Code issues in task functions not properly updating status

### Recommended Actions

Based on diagnostic results:

- If tasks show successful execution but status not updated:

  - Check the TaskManager status update code
  - Run a one-time fix script to update the status of completed tasks

- If tasks have not executed:
  - Verify Celery worker status
  - Check Redis connectivity and memory usage
  - Examine Celery task queue for backlog

## Progress Tracking

The command includes progress indicators to help troubleshoot long-running checks:

```
[Line ~62] Starting task status check for tasks older than 906 hours...
[Line ~65] Querying database for stuck tasks... This may take a moment
[Line ~75] Database query complete. Processing results...
[Line ~95] Processing complete. Found 245 stuck task types.
[Line ~106] Analyzing task type 1/245: task_manager.django.tasks.execute_signal
```

These indicators help identify where the command might be hanging and track progress through large datasets.

## Implementation Location

The command is located at:

```
breathecode/monitoring/management/commands/check_task_status.py
```
