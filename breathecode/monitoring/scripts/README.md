# Monitoring Scripts

A monitoring script is something that you want to execute recurrently withing the breathecode API, for example:

`scripts/alert_pending_leads.py` is a small python script that checks if there is FormEntry Marketing module database that are pending processing.

You can create a monitoring script to remind academy staff members about things, or to remind students about pending homework, etc.

## Stepts to create a new script:

1. create a new python file inside `./breathecode/monitoring/scripts`
2. make sure your script starts with this content always:

```py
#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""
from breathecode.utils import ScriptNotification
# start your code here
```

3. You have access to the entire breathecode API from here, you can import models, services or any other class or variable from any file.
4. You can raise a `ScriptNotification` to notify for `MINOR` or `CRITICAL` reasons, for example:

```py
# here we are raising a notification because there are 2 pending tasks
raise ScriptNotification("There are 2 pending taks", status='MINOR')
```
5. If you dont raise any ScriptNotification and there are no other Exceptions in the script, it will be considered successfull and **no notifications** will trigger.
6. When a ScriptNotification has been raise the Application owner will recive a notification to the application.email and slack channel configured for notifications.
7. Check for other scripts as examples.
8. Test your script.

## Testing your script

You can test your scripts by running the following command:

```bash
$ python manage.py run_script <file_name>

# For example you can test the alert_pending_leads script like this:
$ python manage.py run_script alert_pending_leads.py
```

## Example Script

The following script checks for pending leads to process:

```py
#!/usr/bin/env python
"""
Alert when there are Form Entries with status = PENDING
"""
from breathecode.marketing.models import FormEntry
from django.db.models import Q
from breathecode.utils import ScriptNotification

# check the database for pending leads
pending_leads = FormEntry.objects.filter(storage_status="PENDING").filter(Q(academy__id=academy.id) | Q(location=academy.slug))

# trigger notification because pending leads were found
if len(pending_leads) > 0:
    raise ScriptNotification(f"Warning there are {len(pending_leads)} pending form entries", status='MINOR')

# You can print this and it will show on the script results
print("No pending leads")
```