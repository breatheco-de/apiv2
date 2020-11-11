from celery import shared_task, Task
from .models import SlackTeam
from .actions import sync_slack_team_channel, sync_slack_team_users

class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5 } 
    retry_backoff = True

@shared_task
def async_slack_team_channel(team_id):
    return sync_slack_team_channel(team_id)
    
@shared_task
def async_slack_team_users(team_id):
    return sync_slack_team_users(team_id)