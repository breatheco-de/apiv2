#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""

# flake8: noqa: F821

from breathecode.authenticate.models import GithubAcademyUser
from breathecode.utils import ScriptNotification

pending = GithubAcademyUser.objects.filter(academy=academy).exclude(storage_action__in=["ADD", "DELETE"])

if pending.exists():
    invite = pending.filter(storage_action="INVITE")
    ignore = pending.filter(storage_action="IGNORE")
    raise ScriptNotification(
        f"There are {str(invite.count())} github users marked as invite and {str(ignore.count())} " "marked as ignore",
        status="CRITICAL",
        title=f"There are {str(invite.count())} github users marked as invite and {str(ignore.count())} "
        "marked as ignore",
        slug=f"{str(invite.count())}-invite-and-{str(ignore.count())}-ignore",
    )

print("All good")
