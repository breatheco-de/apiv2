import logging
import os

import requests

logger = logging.getLogger(__name__)

TRACK_URL = "https://cdp.4geeks.us/v1/track"


class CdpTrackError(Exception):
    pass


def build_track_body(entry) -> dict | None:
    """Build the CDP track payload from a FormEntry. None when there is no event tag."""
    tags = entry.tags or ""
    if not str(tags).strip():
        return None

    first_name = entry.first_name or ""
    last_name = entry.last_name or ""

    return {
        "event": tags,
        "eventId": str(entry.id),
        "source": "breathecode",
        "email": entry.email,
        "phone": entry.phone,
        "traits": {
            "name": f"{first_name} {last_name}".strip(),
            "country": entry.country,
        },
        "properties": {
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "tags": tags,
            "course": entry.course,
            "location": entry.location,
            "language": entry.language,
            "client_comments": entry.client_comments,
            "utm_url": entry.utm_url,
            "utm_source": entry.utm_source,
            "utm_medium": entry.utm_medium,
            "utm_campaign": entry.utm_campaign,
            "utm_content": entry.utm_content,
            "utm_term": entry.utm_term,
            "utm_plan": entry.utm_plan,
            "product": entry.product,
            "persona": entry.persona,
            "product_persona": entry.product_persona,
            "variant": entry.variant,
            "experiment_id": entry.experiment_id,
        },
    }


def track_form_entry(entry) -> bool:
    """POST the lead to the CDP. Returns False when there is nothing to send."""
    api_key = os.getenv("CDP_API_KEY") or ""
    if not api_key:
        logger.info("CDP_API_KEY is empty, skipping lead track")
        return False

    body = build_track_body(entry)
    if body is None:
        logger.info("FormEntry %s has no tags, skipping lead track", entry.id)
        return False

    response = requests.post(
        TRACK_URL,
        json=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise CdpTrackError(f"CDP track failed with status {response.status_code}")

    return True
