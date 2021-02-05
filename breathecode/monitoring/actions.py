import logging, datetime, hashlib, requests, json, re, os, subprocess, sys
from django.utils import timezone
from breathecode.utils import ScriptNotification
from breathecode.services.slack.actions.monitoring import render_snooze_text_endpoint
logger = logging.getLogger(__name__)
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"

def get_website_text(endp):
    """Make a request to get the content of the given URL."""

    headers = {
        'User-Agent': USER_AGENT
    }

    url = endp.url
    status_code = 404
    status_text = ""
    payload = None
    try:
        r = requests.get(url, headers=headers, timeout=2)
        content_type = r.headers['content-type']
        length = 0
        if 'content-length' in r.headers:
            length = r.headers['content-length']
        status_code = r.status_code

        if endp.test_pattern is not None and endp.test_pattern != "" and status_code == 200:
            if int(length) > 3000:
                status_code = 400
                status_text = "Timeout: The payload of this request is too long (more than 3 MB), remove the test_pattern to avoid timeout"
            else:
                payload = r.text
    except requests.Timeout:
        status_code = 500
        status_text = "Connection Timeout"
    except requests.ConnectionError:
        status_code = 404
        status_text = "Connection Error"

    logger.debug(f"Tested {url} {status_code}")
    endp.last_check = timezone.now()
    if status_code > 399:
        endp.status = 'CRITICAL'
        endp.severity_level = 100
        endp.status_text = "Status above 399"
    elif status_code > 299:
        endp.status = 'MINOR'
        endp.severity_level = 5
        endp.status_text = "Status in the 3xx range, maybe a cached reponse?"
    elif status_code > 199:
        endp.severity_level = 5
        endp.status = 'OPERATIONAL'
        endp.status_text = "Status withing the 2xx range"
    else:
        endp.status = 'MINOR'
        endp.severity_level = 0
        endp.status_text = "Uknown status code, lower than 200"

    if endp.test_pattern is not None and endp.test_pattern != "" and status_code == 200 and payload:
        if not re.search(endp.test_pattern, payload):
            endp.status = 'MINOR'
            endp.severity_level = 5
            endp.status_text = f"Status is 200 but regex {endp.test_pattern} was rejected"

    print("status", endp.status_text)
    endp.status_code = status_code
    endp.response_text = payload
    endp.save()
        
    return endp


def run_app_diagnostic(app, report=False):

    failed_endpoints = [] #data to be send to slack
    results = {
        "severity_level": 0,
        "details": ""
    }
    logger.debug(f"Testing application {app.title}")
    now = timezone.now()
    _endpoints = app.endpoint_set.all()
    for endpoint in _endpoints:
        if endpoint.last_check is not None and endpoint.last_check > now - timezone.timedelta(minutes = endpoint.frequency_in_minutes):
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
        logger.debug(f"Testing endpoint: {endpoint.url} ")
        e.status = 'LOADING'
        e.save()

        e = get_website_text(endpoint)
        if e.status != 'OPERATIONAL':
            if e.severity_level > results["severity_level"]:
                results["severity_level"] = e.severity_level
            if e.special_status_text:
                results["details"] += e.special_status_text
            if e.status not in results:
                results[e.status] = []
            results[e.status].append(e.url)
            failed_endpoints.append(e)

    if results["severity_level"] == 0:
        results["status"] = 'OPERATIONAL'
    elif results["severity_level"] > 10:
        results["status"] = 'CRITICAL'
    else:
        results["status"] = 'MINOR'

    # results["url"] = endpoint.url
    results["text"] = json.dumps(results, indent=4)

    app.status = results["status"]

    results["slack_payload"] =  render_snooze_text_endpoint(failed_endpoints) #converting to json to send to slack

    if results["details"] != "":
        app.response_text = results["details"]
    else:
        results["details"] = results["text"]
        app.response_text = results["text"]

    app.save()

    return results


def run_script(script):

    results = {
        "severity_level": 0,
        "details": ""
    }

    from io import StringIO
    import contextlib

    @contextlib.contextmanager
    def stdoutIO(stdout=None):
        old = sys.stdout
        if stdout is None:
            stdout = StringIO()
        sys.stdout = stdout
        yield stdout
        sys.stdout = old

    content = None
    if script.script_slug != "" and script.script_slug is not None and script.script_slug != "other":
        dir_path = os.path.dirname(os.path.realpath(__file__))
        header = """
# from django.conf import settings
# import breathecode.settings as app_settings

# settings.configure(INSTALLED_APPS=app_settings.INSTALLED_APPS,DATABASES=app_settings.DATABASES)

# import django
# django.setup()
        """
        content = header + open(f"{dir_path}/scripts/{script.script_slug}.py").read()
    elif script.script_body is not None and script.script_body != "":
        content = script.script_body
    else:
        raise Exception("Script not found or its body is empty: "+script.script_slug)

    if content is not None and content != "":
        local = { "result": { "details": "", "status": "OPERATIONAL" } }
        with stdoutIO() as s:
            try:
                exec(content, { "academy": script.application.academy }, local)
                script.status_code = 0
                script.status = 'OPERATIONAL'

            except ScriptNotification as e:
                script.status_code = 1
                if e.status is not None:
                    script.status = e.status
                else:
                    script.status = 'MINOR'
                print(e)
            except Exception as e:
                script.status_code = 1
                script.status = 'CRITICAL'
                print(e)

        script.last_run = timezone.now()
        script.response_text = s.getvalue()
        script.save()

        result = {
            "status": script.status,
            "details": script.response_text
        }

        return result

    return content is not None and script.status_code == 0