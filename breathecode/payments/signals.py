"""For each signal you want other apps to be able to receive, you have to declare a new variable here like this."""

from task_manager.django.dispatch import Emisor

emisor = Emisor("breathecode.payments")

# consume a service
consume_service = emisor.signal("consume_service")

# refund the units in case of error
reimburse_service_units = emisor.signal("reimburse_service_units")

# manage of permissions for the service
lose_service_permissions = emisor.signal("lose_service_permissions")
grant_service_permissions = emisor.signal("grant_service_permissions")
revoke_service_permissions = emisor.signal("revoke_service_permissions")

# proxy to m2m_changed in Event.service_items
update_plan_m2m_service_items = emisor.signal("update_plan_m2m_service_items")

# Plan adquired
planfinancing_created = emisor.signal("planfinancing_created")
subscription_created = emisor.signal("subscription_created")
grant_plan_permissions = emisor.signal("grant_plan_permissions")
revoke_plan_permissions = emisor.signal("revoke_plan_permissions")
