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
    r = requests.get(url, headers=headers)

    logger.debug(f"Tested {url} {r.status_code}")
    endp.last_check = timezone.now()
    if r.status_code > 399:
        endp.status = 'CRITICAL'
        endp.severity_level = 100
        endp.status_text = "Status above 399"
    elif r.status_code > 299:
        endp.status = 'MINOR'
        endp.severity_level = 5
        endp.status_text = "Status in the 3xx range, maybe a cached reponse?"
    elif r.status_code > 199:
        endp.severity_level = 5
        endp.status = 'OPERATIONAL'
        endp.status_text = "Status withing the 2xx range"
    else:
        endp.status = 'MINOR'
        endp.severity_level = 0
        endp.status_text = "Uknown status code, lower than 200"

    if endp.test_pattern is not None and endp.test_pattern != "" and r.status_code == 200:
        if not re.search(endp.test_pattern, r.text):
            endp.status = 'MINOR'
            endp.severity_level = 5
            endp.status_text = f"Status is 200 but regex {endp.test_pattern} was rejected"

    endp.status_code = r.status_code
    endp.response_text = r.text
    endp.save()
        
    return endp


def run_app_diagnostig(app, report=False):

    results = {
        "severity_level": 0
    }
    logger.debug(f"Testing application {app.title}")
    _endpoints = app.endpoint_set.all()
    for endpoint in _endpoints:
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

    app.status = results["status"]
    app.response_text = results["text"]
    app.save()

    return results