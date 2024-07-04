import csv
import json
import logging
import os
import re
import sys
import time
from io import StringIO

import requests
from django.utils import timezone

from breathecode.admissions.models import Academy
from breathecode.authenticate.models import AcademyAuthSettings
from breathecode.services.github import Github
from breathecode.services.slack.actions.monitoring import render_snooze_script, render_snooze_text_endpoint
from breathecode.utils import ScriptNotification
from breathecode.utils.script_notification import WrongScriptConfiguration
from capyc.rest_framework.exceptions import ValidationException

from .models import CSVDownload, Endpoint, RepositorySubscription, RepositoryWebhook, StripeEvent

logger = logging.getLogger(__name__)

USER_AGENT = "BreathecodeMonitoring/1.0"
SCRIPT_HEADER = """
# from django.conf import settings
# import breathecode.settings as app_settings

# settings.configure(INSTALLED_APPS=app_settings.INSTALLED_APPS,DATABASES=app_settings.DATABASES)

# import django
# django.setup()
"""


def test_link(url, test_pattern=None):

    headers = {"User-Agent": USER_AGENT}

    result = {
        "url": url,
        "status_code": 404,
        "status_text": "",
        "payload": None,
    }

    try:
        r = requests.get(url, headers=headers, timeout=2)
        length = 0
        if "content-length" in r.headers:
            length = r.headers["content-length"]
        result["status_code"] = r.status_code

        # if status is one error, we should need see the status text
        result["payload"] = r.text

        if (
            test_pattern is None
            and not (result["status_code"] >= 200 and result["status_code"] <= 299)
            and int(length) > 3000
        ):
            result["status_code"] = 400
            result["status_text"] = (
                "Timeout: The payload of this request is too long "
                "(more than 3 MB), remove the test_pattern to avoid timeout"
            )

    except requests.Timeout:
        result["status_code"] = 500
        result["status_text"] = "Connection Timeout"
    except requests.ConnectionError:
        result["status_code"] = 404
        result["status_text"] = "Connection Error 404"

    logger.debug(f'Tested {url} {result["status_text"]} with {result["status_code"]}')
    return result


def subscribe_repository(subs_id, settings=None):

    subscription = RepositorySubscription.objects.filter(id=subs_id).first()
    try:
        if subscription is None:
            raise Exception(f"Invalid subscription id {subs_id}")

        if settings is None:
            settings = AcademyAuthSettings.objects.filter(academy__id=subscription.owner.id).first()
            if settings is None:
                raise Exception(
                    f"Github credentials and settings have not been found for the academy {subscription.owner.id}"
                )

        if settings.academy.id != subscription.owner.id:
            raise Exception("Provided auth settings don't belong to the academy subscription owner")

        _owner, _repo_name = subscription.get_repo_name()
        gb = Github(org=settings.github_username, token=settings.github_owner.credentialsgithub.token)
        result = gb.subscribe_to_repo(_owner, _repo_name, subscription.token)

        subscription.status = "OPERATIONAL"
        subscription.status_message = "OK"
        subscription.hook_id = result["id"]
        subscription.save()
    except Exception as e:
        subscription.status = "CRITICAL"
        subscription.status_message = "Error subscribing to repo: " + str(e)
        subscription.save()
    return subscription


def get_website_text(endp):
    """Make a request to get the content of the given URL."""

    res = test_link(endp.url, endp.test_pattern)
    status_code = res["status_code"]
    payload = res["payload"]

    endp.last_check = timezone.now()

    if status_code > 399:
        endp.status = "CRITICAL"
        endp.severity_level = 100
        endp.status_text = "Status above 399"

    elif status_code > 299:
        endp.status = "MINOR"
        endp.severity_level = 5
        endp.status_text = "Status in the 3xx range, maybe a cached reponse?"

    elif status_code > 199:
        endp.severity_level = 5
        endp.status = "OPERATIONAL"
        endp.status_text = "Status withing the 2xx range"

    else:
        endp.status = "MINOR"
        endp.severity_level = 0
        endp.status_text = "Uknown status code, lower than 200"

    if endp.test_pattern and status_code == 200 and payload:
        if not re.search(endp.test_pattern, payload):
            endp.response_text = payload
            endp.status = "MINOR"
            endp.severity_level = 5
            endp.status_text = f"Status is 200 but regex {endp.test_pattern} was rejected"
        else:
            endp.response_text = None

    elif not (status_code >= 200 and status_code <= 299):
        endp.response_text = payload
    else:
        endp.response_text = None

    endp.status_code = status_code
    endp.save()

    return endp


def run_app_diagnostic(app, report=False):

    failed_endpoints = []  # data to be send to slack
    results = {"severity_level": 0, "details": ""}
    logger.debug(f"Testing application {app.title}")
    now = timezone.now()
    _endpoints = app.endpoint_set.all()
    for endpoint in _endpoints:
        if endpoint.last_check is not None and endpoint.last_check > now - timezone.timedelta(
            minutes=endpoint.frequency_in_minutes
        ):
            logger.debug(f"Ignoring {endpoint.url} because frequency hast not been met")
            endpoint.status_text = "Ignored because its paused"
            endpoint.save()
            continue

        if endpoint.paused_until is not None and endpoint.paused_until > now:
            logger.debug(f"Ignoring endpoint:{endpoint.url} monitor because its paused")
            endpoint.status_text = "Ignored because its paused"
            endpoint.save()
            continue

        # Starting the test
        logger.debug(f"Testing endpoint: {endpoint.url}")
        endpoint.status = "LOADING"
        endpoint.save()

        e = get_website_text(endpoint)
        if e.status != "OPERATIONAL":
            if e.severity_level > results["severity_level"]:
                results["severity_level"] = e.severity_level
            if e.special_status_text:
                results["details"] += e.special_status_text
            if e.status not in results:
                results[e.status] = []
            results[e.status].append(e.url)
            failed_endpoints.append(e)

    if results["severity_level"] == 0:
        results["status"] = "OPERATIONAL"
    elif results["severity_level"] > 10:
        results["status"] = "CRITICAL"
    else:
        results["status"] = "MINOR"

    results["slack_payload"] = render_snooze_text_endpoint(failed_endpoints)  # converting to json to send to slack

    # JSON Details to be shown on the error report
    results["details"] = json.dumps(results, indent=4)

    app.status = results["status"]
    app.response_text = results["text"]
    app.save()

    return results


def run_endpoint_diagnostic(endpoint_id):
    endpoint = Endpoint.objects.get(id=endpoint_id)
    results = {"severity_level": 0, "details": "", "log": ""}

    logger.debug(f"Testing endpoint {endpoint.url}")
    now = timezone.now()

    if endpoint.last_check and endpoint.last_check > now - timezone.timedelta(minutes=endpoint.frequency_in_minutes):
        logger.debug(f"Ignoring {endpoint.url} because frequency hast not been met")
        endpoint.status_text = "Ignored because its paused"
        endpoint.save()
        return False

    if endpoint.paused_until and endpoint.paused_until > now:
        logger.debug(f"Ignoring endpoint:{endpoint.url} monitor because its paused")
        endpoint.status_text = "Ignored because its paused"
        endpoint.save()
        return False

    # Starting the test
    logger.debug(f"Testing endpoint: {endpoint.url}")
    endpoint.status = "LOADING"
    endpoint.save()

    e = get_website_text(endpoint)
    results["text"] = e.response_text
    if e.status != "OPERATIONAL":
        if e.severity_level > results["severity_level"]:
            results["severity_level"] = e.severity_level
        if e.special_status_text:
            results["details"] += e.special_status_text
        if e.status not in results:
            results[e.status] = []
        results[e.status].append(e.url)

    if results["severity_level"] == 0:
        results["status"] = "OPERATIONAL"
    elif results["severity_level"] > 10:
        results["status"] = "CRITICAL"
    else:
        results["status"] = "MINOR"

    results["slack_payload"] = render_snooze_text_endpoint([endpoint])  # converting to json to send to slack

    results["details"] = json.dumps(results, indent=4)
    endpoint.response_text = results["text"]

    endpoint.save()
    return results


def run_script(script):
    results = {
        "severity_level": 0,
    }

    import contextlib
    from io import StringIO

    @contextlib.contextmanager
    def stdout_io(stdout=None):
        old = sys.stdout
        if stdout is None:
            stdout = StringIO()
        sys.stdout = stdout
        yield stdout
        sys.stdout = old

    content = None
    exception = None
    if script.script_slug and script.script_slug != "other":
        dir_path = os.path.dirname(os.path.realpath(__file__))
        header = SCRIPT_HEADER
        content = header + open(f"{dir_path}/scripts/{script.script_slug}.py").read()

    elif script.script_body:
        content = script.script_body

    else:
        exception = WrongScriptConfiguration(f"Script not found or its body is empty: {script.script_slug}")

    if content or exception:
        local = {"result": {"status": "OPERATIONAL"}}
        with stdout_io() as s:
            try:
                if exception:
                    raise exception

                if script.application is None:
                    raise Exception(f"Script {script.script_slug} does not belong to any application")

                exec(
                    content,
                    {
                        "academy": script.application.academy,
                        "ADMIN_URL": os.getenv("ADMIN_URL", ""),
                        "API_URL": os.getenv("API_URL", ""),
                    },
                    local,
                )
                script.status_code = 0
                script.status = "OPERATIONAL"
                script.special_status_text = "OK"
                results["severity_level"] = 5
                script.response_text = s.getvalue()

            except ScriptNotification as e:
                script.status_code = 1
                script.response_text = str(e)
                if e.title is not None:
                    script.special_status_text = e.title

                if e.btn_url is not None:
                    results["btn"] = {"url": e.btn_url, "label": "More details"}
                    if e.btn_label is not None:
                        results["btn"]["label"] = e.btn_label
                else:
                    results["btn"] = None

                if e.status is not None:
                    script.status = e.status
                    results["severity_level"] = 5 if e.status != "CRITICAL" else 100
                else:
                    script.status = "MINOR"
                    results["severity_level"] = 5
                results["error_slug"] = e.slug

            except WrongScriptConfiguration as e:
                script.special_status_text = str(e)[:255]
                script.response_text = str(e)
                script.status_code = 1
                script.status = "CRITICAL"
                results["error_slug"] = "wrong-configuration"
                results["btn"] = None
                results["severity_level"] = 100

            except Exception as e:
                import traceback

                script.special_status_text = str(e)[:255]
                script.response_text = "".join(traceback.format_exception(None, e, e.__traceback__))
                script.status_code = 1
                script.status = "CRITICAL"
                results["error_slug"] = "unknown"
                results["btn"] = None
                results["severity_level"] = 100

        script.last_run = timezone.now()
        script.save()

        results["status"] = script.status
        results["text"] = script.response_text
        results["title"] = script.special_status_text
        results["slack_payload"] = render_snooze_script([script])  # converting to json to send to slack

        return results

    return content is not None and script.status_code == 0


def download_csv(module, model_name, ids_to_download, academy_id=None):

    download = CSVDownload()

    try:
        downloads_bucket = os.getenv("DOWNLOADS_BUCKET", None)
        if downloads_bucket is None:
            raise Exception("Unknown DOWNLOADS_BUCKET configuration, please set env variable")

        # separated downloads by academy
        academy = Academy.objects.filter(id=academy_id).first()
        download.name = ""
        if academy is not None:
            download.academy = academy
            download.name += academy.slug

        # import model (table) being downloaded
        import importlib

        model = getattr(importlib.import_module(module), model_name)

        # finish the file name with <academy_slug>+<model_name>+<epoc_time>.csv
        download.name = model_name + str(int(time.time())) + ".csv"
        download.save()

        meta = model._meta
        field_names = [field.name for field in meta.fields]
        # rebuild query from the admin
        queryset = model.objects.filter(pk__in=ids_to_download)

        # write csv
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow((getattr(obj, field) for field in field_names))

        # upload to google cloud bucket
        from ..services.google_cloud import Storage

        storage = Storage()
        cloud_file = storage.file(os.getenv("DOWNLOADS_BUCKET", None), download.name)
        cloud_file.upload(buffer.getvalue(), content_type="text/csv")
        download.url = cloud_file.url()
        download.status = "DONE"
        download.save()
        return True
    except Exception as e:
        download.status = "ERROR"
        download.status_message = str(e)
        download.save()
        return False


def unsubscribe_repository(subs_id, force_delete=True):
    try:
        subs = RepositorySubscription.objects.filter(id=subs_id).first()

        if subs.hook_id is None:
            raise Exception("Subscription is missing a github hook id")

        settings = AcademyAuthSettings.objects.filter(academy__id=subs.owner.id).first()
        gb = Github(org=settings.github_username, token=settings.github_owner.credentialsgithub.token)

        _owner, _repo_name = subs.get_repo_name()
        gb.unsubscribe_from_repo(_owner, _repo_name, subs.hook_id)

        # you can delete the subscription after unsubscribing
        if force_delete:
            subs.delete()
        else:
            subs.status = "DISABLED"
            subs.hook_id = None
            subs.status_message = "disabled successfully"
            subs.save()
            return subs

        return True
    except Exception as e:
        subs.status = "CRITICAL"
        subs.status_message = "Cannot unsubscribe subscription: " + str(e)
        subs.save()
        return False


def add_github_webhook(context: dict, academy_slug: str):
    """Add one incoming webhook request to log"""

    if not context or not len(context):
        logger.error("Missing webhook payload")
        return None

    if "action" not in context:
        if context["scope"] == "push":
            context["action"] = "push"
        else:
            logger.error("Missing action param on the webhook payload")
            logger.error(context)
            return None

    webhook = RepositoryWebhook(webhook_action=context["action"], scope=context["scope"], academy_slug=academy_slug)

    if "repository" in context:
        webhook.repository = context["repository"]["html_url"]

    webhook.payload = json.dumps(context)
    webhook.status = "PENDING"
    webhook.save()

    return webhook


def add_stripe_webhook(context: dict) -> StripeEvent:
    try:
        event = StripeEvent(
            stripe_id=context["id"],
            type=context["type"],
            status="PENDING",
            data=context["data"],
            request=context["request"],
        )
        event.save()

    except Exception:
        raise ValidationException("Invalid stripe webhook payload", code=400, slug="invalid-stripe-webhook-payload")

    return event
