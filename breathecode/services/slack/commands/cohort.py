import os

from breathecode.admissions.models import Cohort, CohortUser
from ..decorator import command
from ..utils import to_string
"""
Possible parameters for this command:
- users: Array of user slack_ids mentioned inside the slack command text content
- user_id: Slack user ID of the message author
- team_id: Slack team_id where the message was posted
- channel_id: Slack channel_id where the message was posted
- text: Content of the slack channel

"""


@command(only='staff')
def execute(channel_id, **context):

    response = {"blocks": []}
    response["blocks"].append(render_cohort(channel_id=channel_id))

    return response


def render_cohort(channel_id):

    cohort = Cohort.objects.filter(slackchannel__slack_id=channel_id).first()
    if cohort is None:
        raise Exception(
            f"Cohort was not found as slack channel, make sure the channel name matches the cohort slug"
        )

    teachers = CohortUser.objects.filter(cohort=cohort,
                                         role__in=['TEACHER', 'ASSISTANT'])
    return {
        "type": "section",
        "text": {
            "type":
            "mrkdwn",
            "text":
            f"""
*Cohort name:* {cohort.name}
*Start Date*: {cohort.kickoff_date}
*End Date*: {cohort.ending_date}
*Current day:*: {cohort.current_day}
*Stage:* {cohort.stage}
*Teachers:* {', '.join([cu.user.first_name + ' ' + cu.user.last_name for cu in teachers])}
"""
        }
    }
