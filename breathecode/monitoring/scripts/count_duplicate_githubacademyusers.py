#!/usr/bin/env python
"""
Count Duplicate Github Academy Users
"""

# flake8: noqa: F821

from breathecode.utils import ScriptNotification
from breathecode.authenticate.models import GithubAcademyUser

# Query to find duplicate users for the same academy
duplicate_users = (
    GithubAcademyUser.objects.values("user__id", "academy__id")
    .annotate(user_count=Count("user__id"))
    .filter(user_count__gt=1)
)

# Extract duplicate user_ids and academy_ids from the query result
duplicate_user_ids = [entry["user__id"] for entry in duplicate_users]
duplicate_academy_ids = [entry["academy__id"] for entry in duplicate_users]

# Find the actual duplicate records
duplicate_records = GithubAcademyUser.objects.filter(
    Q(user__id__in=duplicate_user_ids) & Q(academy__id__in=duplicate_academy_ids)
)

duplicate_amount = duplicate_records.count()
if duplicate_amount > 0:

    def to_string(_gu):
        return _gu.user.first_name + " " + _gu.user.last_name + " from academy: " + _gu.academy.name

    duplicates = ("\n").join(["- " + to_string(gu) for gu in duplicate_records])

    raise ScriptNotification(
        f"Following users have duplicate academy users, this problem needs to be fixed before we can bill the provisioning services: \n {duplicates} ",
        status="CRITICAL",
        title=f"There are {str(len(duplicate_amount))} duplicate Github Academy Users",
        slug="duplicate-github-academy-users",
    )

else:
    print("No github academy users are duplicated")
