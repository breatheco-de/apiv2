# Webhook Auto-Registration System

## Overview

The BreatheCode API includes an auto-registration system for webhook receivers that eliminates the need to write boilerplate code for standard webhook events. Instead of manually creating receiver functions, you can configure events in `settings.HOOK_EVENTS_METADATA` and they will be automatically registered.

## Benefits

1. **Single Source of Truth**: All webhook configuration in one place
2. **Less Boilerplate**: No need to write repetitive receiver functions
3. **Consistency**: All auto-registered receivers follow the same pattern
4. **Maintainability**: Add new webhooks by just adding metadata
5. **Documentation**: Metadata serves as inline documentation

## How It Works

### 1. Configuration (`breathecode/notify/utils/hook_events.py`)

Define webhook events in `HOOK_EVENTS_METADATA` (imported into settings.py):

```python
HOOK_EVENTS_METADATA = {
    "assignment.assignment_created": {
        # Required by Django REST Hooks
        "action": "assignments.Task.assignment_created",
        
        # For API documentation and filtering
        "category": "assignments",
        "description": "Triggered when a new assignment is created for a student",
        "model": "assignments.Task",
        
        # For auto-registration (all three required)
        "signal": "breathecode.assignments.signals.assignment_created",
        "sender": "breathecode.assignments.models.Task",
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
        "event_action": "assignment_created",
    },
}
```

### 2. Auto-Registration (`breathecode/notify/utils/auto_register_hooks.py`)

The system automatically:
1. Imports the signal and sender model
2. Creates a receiver function
3. Connects it to the signal
4. Handles serialization and payload delivery

### 3. Initialization (`breathecode/notify/apps.py`)

Receivers are registered when Django starts:

```python
def ready(self):
    from . import receivers  # Manual receivers
    from .utils.auto_register_hooks import auto_register_webhook_receivers
    
    auto_register_webhook_receivers()  # Auto-register from metadata
```

## Configuration Fields

### Required Fields (for all events)

| Field | Description | Example |
|-------|-------------|---------|
| `action` | Django REST Hooks action string | `"assignments.Task.created+"` |
| `description` | Human-readable description | `"Triggered when..."` |
| `app` | App name (auto-derived from action) | `"assignments"` |
| `model` | Source model (auto-derived from action) | `"assignments.Task"` |

### Optional Fields (for auto-registration)

| Field | Description | Required for Auto-Reg |
|-------|-------------|-----------------------|
| `signal` | Import path to Django signal | Auto-derived† |
| `sender` | Import path to sender model | Auto-derived† |
| `serializer` | Import path to serializer class | No* |
| `event_action` | Action name for HookManager | Auto-derived† |
| `auto_register` | Set to `False` to skip | No |

\* If no serializer is provided, raw instance data is sent

† **All auto-derived from the action string** if not explicitly provided. The system converts:
```
From action: "app.Model.signal_name"

Auto-derived:
- signal       → "breathecode.app.signals.signal_name"
- sender       → "breathecode.app.models.Model"
- event_action → "signal_name"
```

Only specify these explicitly when:
- Signal name differs from action (e.g., `student_edu_status_updated` vs `edu_status_updated`)
- You need custom behavior

## Event Types

### Type 1: Auto-Triggered by Django Signals

These use Django's built-in `post_save` or `post_delete` signals. No configuration needed beyond the basic fields:

```python
"cohort_user.added": {
    "action": "admissions.CohortUser.created+",
    "category": "admissions",
    "description": "Triggered when a student is added to a cohort",
    "model": "admissions.CohortUser",
    # No signal config - handled by post_save receiver
}
```

### Type 2: Auto-Registered Custom Signals

These use custom signals and are auto-registered. **Signal, sender, and event_action are all auto-derived from the action:**

```python
"assignment.assignment_created": {
    "action": "assignments.Task.assignment_created",
    "category": "assignments",
    "description": "Triggered when a new assignment is created",
    "model": "assignments.Task",
    # Everything auto-derived from action! ✨
    # Derived: signal = "breathecode.assignments.signals.assignment_created"
    # Derived: sender = "breathecode.assignments.models.Task"
    # Derived: event_action = "assignment_created"
    "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
}
```

**Minimal Configuration:**
```python
"cohort.cohort_stage_updated": {
    "action": "admissions.Cohort.cohort_stage_updated",
    "category": "admissions",
    "description": "Triggered when cohort stage changes",
    "model": "admissions.Cohort",
    "serializer": "breathecode.admissions.serializers.CohortHookSerializer",
    # That's it! Only 5 fields needed, everything else is auto-derived
}
```

**Only specify explicitly when signal name differs:**

```python
"cohort_user.edu_status_updated": {
    "action": "admissions.CohortUser.edu_status_updated",
    "category": "admissions",
    "description": "Triggered when educational status changes",
    "model": "admissions.CohortUser",
    # Signal name differs from action - must be explicit
    "signal": "breathecode.admissions.signals.student_edu_status_updated",
    # Sender and event_action still auto-derived!
    "serializer": "breathecode.admissions.serializers.CohortUserHookSerializer",
}
```

### Type 3: Manual Receivers with Custom Logic

For receivers that need custom logic beyond standard webhook delivery:

```python
"session.mentorship_session_status": {
    "action": "mentorship.MentorshipSession.mentorship_session_status",
    "category": "mentorship",
    "description": "Triggered when session status changes",
    "model": "mentorship.MentorshipSession",
    "signal": "breathecode.mentorship.signals.mentorship_session_status",
    "sender": "breathecode.mentorship.models.MentorshipSession",
    "serializer": "breathecode.mentorship.serializers.SessionHookSerializer",
    "event_action": "mentorship_session_status",
    # Prevent auto-registration
    "auto_register": False,
}
```

Then manually define in `breathecode/notify/receivers.py`:

```python
@receiver(mentorship_session_status, sender=MentorshipSession)
def post_mentoring_session_status(sender, instance, **kwargs):
    # Custom logic before webhook delivery
    if instance.status == "STARTED":
        send_mentorship_starting_notification.delay(instance.id)
    
    # Standard webhook delivery
    model_label = get_model_label(instance)
    serializer = SessionHookSerializer(instance)
    HookManager.process_model_event(
        instance,
        model_label,
        "mentorship_session_status",
        payload_override=serializer.data,
        academy_override=instance.mentor.academy,
    )
```

## Adding a New Auto-Registered Webhook

### Step 1: Create the Signal

In your app's `signals.py`:

```python
from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.myapp")
my_custom_event = emisor.signal("my_custom_event")
```

### Step 2: Create the Serializer (Optional)

In your app's `serializers.py`:

```python
from breathecode.utils import serpy

class MyModelHookSerializer(serpy.Serializer):
    id = serpy.Field()
    name = serpy.Field()
    status = serpy.Field()
    # ... other fields
```

### Step 3: Add to HOOK_EVENTS_METADATA

In `breathecode/notify/utils/hook_events.py` (minimal configuration - everything auto-derived!):

```python
HOOK_EVENTS_METADATA = {
    # ... existing events ...
    
    "myapp.my_custom_event": {
        "action": "myapp.MyModel.my_custom_event",
        "category": "myapp",
        "description": "Triggered when something happens to MyModel",
        "model": "myapp.MyModel",
        "serializer": "breathecode.myapp.serializers.MyModelHookSerializer",
        # That's it! Only 5 fields needed
    },
}
```

The system automatically derives everything else from the action:
- `signal` = `breathecode.myapp.signals.my_custom_event`
- `sender` = `breathecode.myapp.models.MyModel`
- `event_action` = `my_custom_event`

### Step 4: Emit the Signal

In your model or view:

```python
from . import signals

class MyModel(models.Model):
    # ... fields ...
    
    def some_method(self):
        # Do something
        # Then emit the signal
        signals.my_custom_event.delay(instance=self, sender=self.__class__)
```

That's it! The webhook receiver is automatically registered and will:
- Listen for the signal
- Serialize the instance using your serializer
- Deliver the webhook to subscribed endpoints

## Debugging

### Check Registered Receivers

```python
# In Django shell
from breathecode.myapp.signals import my_custom_event
print(my_custom_event.receivers)
```

### View Auto-Registration Logs

Auto-registration logs are visible at Django startup with `DEBUG=True`:

```
INFO - Auto-registered 15 webhook receivers, skipped 2
DEBUG - Auto-registered receiver for assignment.assignment_created
DEBUG - Skipping auto-registration for session.mentorship_session_status (auto_register=False)
```

### Test Signal Emission

```python
# In Django shell or test
from breathecode.myapp.models import MyModel
from breathecode.myapp.signals import my_custom_event

instance = MyModel.objects.first()
my_custom_event.send(sender=MyModel, instance=instance)
```

## Migration from Manual to Auto-Registration

### Before (Manual Receiver)

```python
# In breathecode/notify/receivers.py
from breathecode.assignments.models import Task
from breathecode.assignments.serializers import TaskHookSerializer
from breathecode.assignments.signals import assignment_created

@receiver(assignment_created, sender=Task)
def handle_assignment_created(sender, instance, **kwargs):
    logger.debug("HOOK: Assignment created")
    model_label = get_model_label(instance)
    serializer = TaskHookSerializer(instance)
    HookManager.process_model_event(
        instance, 
        model_label, 
        "assignment_created", 
        payload_override=serializer.data
    )
```

### After (Auto-Registered)

```python
# In breathecode/settings.py - just add metadata
HOOK_EVENTS_METADATA = {
    "assignment.assignment_created": {
        "action": "assignments.Task.assignment_created",
        "category": "assignments",
        "description": "Triggered when a new assignment is created",
        "model": "assignments.Task",
        "signal": "breathecode.assignments.signals.assignment_created",
        "sender": "breathecode.assignments.models.Task",
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
        "event_action": "assignment_created",
    },
}

# Remove manual receiver from receivers.py
# That's it! ✨
```

## Best Practices

1. **Use Auto-Registration for Standard Webhooks**
   - No custom logic needed
   - Just send data when signal fires

2. **Use Manual Receivers for Complex Logic**
   - Need to check conditions before sending
   - Need to trigger other tasks
   - Need custom academy_override logic
   - Set `auto_register: False` in metadata

3. **Always Include Serializers**
   - Provides consistent payload structure
   - Documents what data is sent
   - Makes payload predictable for consumers

4. **Use Descriptive Event Names**
   - Format: `category.action_description`
   - Example: `assignment.status_updated` not `assignment.updated`

5. **Document in Metadata**
   - Clear descriptions help API consumers
   - Include when/why event triggers
   - List important fields in payload

## Troubleshooting

### Receiver Not Triggering

1. Check signal is emitted: Add debug logging to signal emission
2. Check auto-registration succeeded: Look for registration logs
3. Check signal/sender imports: Verify paths are correct in metadata
4. Check `auto_register` flag: Ensure it's not set to `False`

### Wrong Payload Structure

1. Check serializer path: Verify import path in metadata
2. Test serializer directly: Serialize instance in shell
3. Check serializer fields: Ensure all needed fields are included

### Import Errors

1. Check all import paths in metadata are valid
2. Ensure signal is defined before auto-registration runs
3. Check for circular import issues

## Performance Considerations

- Auto-registration happens once at startup (minimal overhead)
- Dynamically created receivers have same performance as manual ones
- Serialization happens asynchronously via Celery
- No impact on signal emission performance

## Summary

The auto-registration system provides:
- **Less Code**: Eliminate repetitive receiver functions
- **Single Source of Truth**: All configuration in `HOOK_EVENTS_METADATA`
- **Better Documentation**: Metadata documents all webhooks
- **Consistency**: All receivers follow same pattern
- **Flexibility**: Can still write manual receivers when needed

For most webhook events, you only need to add metadata—no receiver code required!

