#!/usr/bin/env python
"""
Alert which Gitpod users will be deleted soon
"""

# flake8: noqa: F821

import datetime
from breathecode.authenticate.models import GitpodUser
from django.db.models import Q
from django.utils import timezone
from breathecode.utils import ScriptNotification
from breathecode.utils.datetime_integer import from_now

in_three_days = timezone.now() + datetime.timedelta(days=3)

gitpod_users_to_delete = GitpodUser.objects.filter(expires_at__lt=in_three_days).filter(
    Q(academy__id=academy.id) | Q(academy__isnull=True)
)

content_html = ""
for u in gitpod_users_to_delete:
    # beware!! from_now cannot be used inside a map or join function, you have to do a traditional for loop
    if u.user is not None:
        content_html += f"- {u.user.first_name} {u.user.last_name} ({u.github_username}) in {from_now(u.expires_at, include_days=True)}: {u.delete_status} \n"
    else:
        content_html += f"- {u.github_username} in {from_now(u.expires_at, include_days=True)}: {u.delete_status} \n"

if len(gitpod_users_to_delete) > 0:
    raise ScriptNotification(
        f"The following {len(gitpod_users_to_delete)} Gitpod users will be delete soon: \n\n" + content_html,
        status="CRITICAL",
        title=f"{str(len(gitpod_users_to_delete))} Gitpod users from {academy.name} will be deleted",
        slug="gitpod-users-to-delete",
        btn_url=ADMIN_URL + "/admin/gitpod?location=" + academy.slug,
    )

print(f"No gitpod users to delete for {academy.name}")
