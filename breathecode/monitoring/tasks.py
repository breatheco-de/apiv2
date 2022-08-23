from django.utils import timezone
from celery import shared_task, Task
from .actions import run_app_diagnostic, run_script, run_endpoint_diagnostic, download_csv
from .models import Application, MonitorScript, Endpoint, CSVDownload
from breathecode.notify.actions import send_email_message, send_slack_raw
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def test_endpoint(self, endpoint_id):
    logger.debug('Starting monitor_app')
    endpoint = Endpoint.objects.get(id=endpoint_id)

    now = timezone.now()
    if endpoint.paused_until is not None and endpoint.paused_until > now:
        logger.debug(f'Ignoring App: {endpoint.url} monitor because its paused')
        return True

    logger.debug(f'Running diagnostic for: {endpoint.url} ')
    result = run_endpoint_diagnostic(endpoint.id)
    if not result:
        # the endpoint diagnostic did not run.
        return False

    if result['status'] != 'OPERATIONAL':
        if endpoint.application.notify_email:
            send_email_message(
                'diagnostic', endpoint.application.notify_email, {
                    'subject': f'Errors found on app {endpoint.application.title} endpoint {endpoint.url}',
                    'details': result['details']
                })

        if (endpoint.application.notify_slack_channel and endpoint.application.academy
                and hasattr(endpoint.application.academy, 'slackteam')
                and hasattr(endpoint.application.academy.slackteam.owner, 'credentialsslack')):
            send_slack_raw(
                'diagnostic', endpoint.application.academy.slackteam.owner.credentialsslack.token,
                endpoint.application.notify_slack_channel.slack_id, {
                    'subject': f'Errors found on app {endpoint.application.title} endpoint {endpoint.url}',
                    **result,
                })


@shared_task(bind=True, base=BaseTaskWithRetry)
def monitor_app(self, app_id):
    logger.debug('Starting monitor_app')
    endpoints = Endpoint.objects.filter(application__id=app_id).values_list('id', flat=True)
    for endpoint_id in endpoints:
        test_endpoint.delay(endpoint_id)


@shared_task(bind=True, base=BaseTaskWithRetry)
def execute_scripts(self, script_id):
    script = MonitorScript.objects.get(id=script_id)
    logger.debug(f'Starting execute_scripts for {script.script_slug}')
    app = script.application

    now = timezone.now()
    if script.paused_until is not None and script.paused_until > now:
        logger.debug('Ignoring script exec because its paused')
        return True

    result = run_script(script)
    if result['status'] != 'OPERATIONAL':
        logger.debug('Errors found, sending script report to ')
        subject = f'Errors have been found on {app.title} script {script.id} (slug: {script.script_slug})'
        if 'title' in result and result['title'] is not None and result['title'] != '':
            subject = result['title']

        email = None
        if script.notify_email is not None:
            email = script.notify_email
        elif app.notify_email is not None:
            email = app.notify_email

        if email is None:
            logger.debug(
                f'No email set for monitoring app or script, skiping email notification for {script.script_slug}'
            )
        else:
            logger.debug(f'Sending script notification report to {email}')
            send_email_message('diagnostic', email, {
                'subject': subject,
                'details': result['text'],
                'button': result['btn']
            })

        if (app.notify_slack_channel and app.academy and hasattr(app.academy, 'slackteam')
                and hasattr(app.academy.slackteam.owner, 'credentialsslack')):
            try:
                send_slack_raw('diagnostic', app.academy.slackteam.owner.credentialsslack.token,
                               app.notify_slack_channel.slack_id, {
                                   'subject': subject,
                                   **result,
                               })
            except Exception:
                return False
        return False

    return True


@shared_task(bind=True, base=BaseTaskWithRetry)
def async_download_csv(self, module, model_name, ids_to_download):
    logger.debug('Starting to download csv for ')
    return download_csv(module, model_name, ids_to_download)
