"""
For each signal you want other apps to be able to receive, you have to
declare a new variable here like this:
"""
from django.dispatch import Signal

# consume a service
consume_service = Signal()

# refund the units in case of error
reimburse_service_units = Signal()

# manage of permissions for the service
lose_service_permissions = Signal()
grant_service_permissions = Signal()
revoke_service_permissions = Signal()

# automatic renew of plan
renew_plan = Signal()

# notifications
renew_plan_fulfilled = Signal()
renew_plan_rejected = Signal()
