"""
Possible parameters for this command:
- users: Array of user slack_ids mentioned inside the slack command text content
- academies: List of ids of all the academies the current user belongs to
- user_id: Slack user ID of the message author
- team_id: Slack team_id where the message was posted
- channel_id: Slack channel_id where the message was posted
- text: Content of the slack channel

"""

import os
import random

from ..decorator import command
from ..utils import to_string, jump
from ..exceptions import SlackException


@command(capable_of="read_student")
def execute(users, academies, **context):
    from breathecode.admissions.models import CohortUser

    if len(users) == 0:
        raise SlackException("No usernames found on the command", slug="users-not-provided")

    cohort_users = CohortUser.objects.filter(
        user__slackuser__slack_id=users[0], role="STUDENT", cohort__academy__id__in=[academies]
    )

    user = cohort_users.first()
    if user is None:
        raise SlackException(
            f'Student {users[0]} not found on any cohort for your available academies, if you feel you should have access " \
                "to this information maybe you need to be added to the relevant academy for this student',
            slug="cohort-user-not-found",
        )

    user = user.user

    response = {"blocks": []}
    response["blocks"].append(render_student(user, cohort_users))

    return response


def render_student(user, cohort_users):
    from breathecode.authenticate.models import Profile

    avatar_number = random.randint(1, 21)
    avatar_url = os.getenv("API_URL", "") + f"/static/img/avatar-{avatar_number}.png"
    github_username = "not set"
    phone = "not set"
    try:
        if user.profile.github_username:
            github_username = user.profile.github_username

        if user.profile.phone:
            phone = user.profile.phone

        if user.profile.avatar_url:
            avatar_url = user.profile.avatar_url

        else:
            user.profile.avatar_url = avatar_url
            user.profile.save()

    except Profile.DoesNotExist:
        pass

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"""
*Student Name:* {user.first_name} {user.last_name}
*Github*: {github_username}
*Phone*: {phone}
*Email:* {user.email}
*Cohorts:*
```
{jump().join([('- '+cu.cohort.name + ': 🎓' + to_string(cu.educational_status) + ' and 💰' + to_string(cu.finantial_status)) for cu in cohort_users])}
```
""",
        },
        "accessory": {
            "type": "image",
            "image_url": to_string(avatar_url),
            "alt_text": f"{user.first_name} {user.last_name}",
        },
    }
