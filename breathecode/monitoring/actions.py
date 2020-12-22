from django.utils import timezone
import logging, datetime, hashlib, requests, json, re

logger = logging.getLogger(__name__)
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"

def get_website_text(endp):
    url = endp.url
    """Make a request to get the content of the given URL."""

    headers = {
        'User-Agent': USER_AGENT
    }

    status_code = 404
    status_text = ""
    try:
        r = requests.get(url, headers=headers)
        status_code = r.status_code
        status_text = r.text
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

    if endp.test_pattern is not None and endp.test_pattern != "" and status_code == 200:
        if not re.search(endp.test_pattern, r.text):
            endp.status = 'MINOR'
            endp.severity_level = 5
            endp.status_text = f"Status is 200 but regex {endp.test_pattern} was rejected"

    endp.status_code = status_code
    endp.response_text = status_text
    endp.save()
        
    return endp


def run_app_diagnostic(app, report=False):

    results = {
        "severity_level": 0
    }
    logger.debug(f"Testing application {app.title}")
    now = timezone.now()
    _endpoints = app.endpoint_set.all()
    for endpoint in _endpoints:
        if endpoint.last_check is not None and endpoint.last_check > now - timezone.timedelta(minutes = endpoint.frequency_in_minutes):
            logger.debug(f"Ignoring {endpoint.url} because frequency hast not been met")
            continue

        if endpoint.paused_until is not None and endpoint.paused_until > now:
            logger.debug(f"Ignoring endpoint:{endpoint.url} monitor because its paused")
            continue

        e = get_website_text(endpoint)
        if e.status != 'OPERATIONAL':
            if e.severity_level > results["severity_level"]:
                results["severity_level"] = e.severity_level

            if e.status not in results:
                results[e.status] = []
            results[e.status].append(e.url)

    if results["severity_level"] == 0:
        results["status"] = 'OPERATIONAL'
    elif results["severity_level"] > 10:
        results["status"] = 'CRITICAL'
    else:
        results["status"] = 'MINOR'

    results["text"] = json.dumps(results, indent=4)
    results["url"] = endpoint.url

    app.status = results["status"]
    app.response_text = results["text"]
    app.save()

    return results