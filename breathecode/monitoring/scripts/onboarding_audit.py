#!/usr/bin/env python
"""
Checks for users in the academy without any active plans (subscriptions or plan financings).
Creates MonitoringError for each user found without a plan.
"""

# flake8: noqa: F821

from breathecode.authenticate.models import ProfileAcademy
from breathecode.payments.models import PlanFinancing, Subscription
from breathecode.monitoring.models import MonitoringError

# Get all active users in the academy
active_users = ProfileAcademy.objects.filter(
    academy__id=academy.id,
    status="ACTIVE",
    user__isnull=False
).select_related("user")

users_without_plans = []

for profile_academy in active_users:
    user = profile_academy.user
    
    # Check if user has any subscriptions
    has_subscription = Subscription.objects.filter(
        user=user,
    ).exists()
    
    # Check if user has any plan financing
    has_plan_financing = PlanFinancing.objects.filter(
        user=user,
    ).exists()
    
    # If user has neither, they don't have a plan
    if not has_subscription and not has_plan_financing:
        users_without_plans.append({
            "user": user,
            "profile_academy": profile_academy,
        })

# Create MonitoringError for each user without a plan
for user_info in users_without_plans:
    user = user_info["user"]
    profile_academy = user_info["profile_academy"]
    
    MonitoringError.objects.create(
        severity=MonitoringError.CRITICAL,
        title=f"User {user.email} has no active plan",
        description=f"User {user.first_name} {user.last_name} ({user.email}) is active in the academy but has no active subscription or plan financing.",
        details={
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "profile_academy_id": profile_academy.id,
        },
        comments={},
        user=user,
        academy=academy,
    )

if len(users_without_plans) > 0:
    print(f"Found {len(users_without_plans)} users without active plans")
else:
    print("All active users have plans")
