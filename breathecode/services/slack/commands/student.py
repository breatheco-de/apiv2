import os

from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import Profile
from ..decorator import command
from ..utils import to_string, jump
"""
Possible parameters for this command:
- users: Array of user slack_ids mentioned inside the slack command text content
- academies: List of ids of all the academies the current user belongs to
- user_id: Slack user ID of the message author
- team_id: Slack team_id where the message was posted
- channel_id: Slack channel_id where the message was posted
- text: Content of the slack channel

"""


@command(only='staff')
def execute(users, academies, **context):

    if len(users) == 0:
        raise Exception("No usernames found on the command")

    cohort_users = CohortUser.objects.filter(
        user__slackuser__slack_id=users[0],
        role='STUDENT',
        cohort__academy__id__in=[academies])
    user = cohort_users.first()
    if user is None:
        raise Exception(
            f"Student {users[0]} not found on any cohort for your available academies, if you feel you should have access to this information maybe you need to be added to the relevant academy for this student"
        )

    user = user.user

    response = {"blocks": []}
    response["blocks"].append(render_student(user, cohort_users))

    return response


def render_student(user, cohort_users):

    avatar_url = os.getenv("API_URL", "") + "/static/img/avatar.png"
    github_username = "not set"
    phone = "not set"
    try:
        github_username = user.profile.github_username
        avatar_url = user.profile.avatar_url
        phone = user.profile.phone
    except Profile.DoesNotExist:
        pass

    return {
        "type": "section",
        "text": {
            "type":
            "mrkdwn",
            "text":
            f"""
*Student Name:* {user.first_name} {user.last_name}
*Github*: {github_username}
*Phone*: {phone}
*Email:* {user.email}
*Cohorts:* 
```
{jump().join([('- '+cu.cohort.name + ': 🎓' + to_string(cu.educational_status) + ' and 💰' + to_string(cu.finantial_status)) for cu in cohort_users])}
```
"""
        },
        "accessory": {
            "type": "image",
            "image_url": to_string(avatar_url),
            "alt_text": f"{user.first_name} {user.last_name}"
        }
    }
