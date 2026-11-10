import logging
import os

import requests

from breathecode.authenticate.actions import get_user_phone

logger = logging.getLogger(__name__)

TRACK_URL = "https://cdp.4geeks.us/v1/track"
IDENTIFY_URL = "https://cdp.4geeks.us/v1/identify"

# Only these FormEntry tags are sent to the CDP as the event name (from historical form entries).
CDP_EVENT_ALLOWLIST = frozenset(
    {
        "request_more_info",
        "website-lead",
        "newsletter",
        "contact-us",
        "request_downloadable",
        "job-application",
        "financing_guide_download",
    }
)

# FormEntry.custom_fields booleans → CDP consent_granted channels.
CONSENT_FIELD_TO_CHANNEL = {
    "consent_email": "email",
    "consent_sms": "sms",
    "consent_whatsapp": "whatsapp",
}


class CdpTrackError(Exception):
    pass


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def get_event_name(tags) -> str | None:
    """First allowlisted tag from a comma-separated tags string, or None."""
    for tag in str(tags or "").split(","):
        tag = tag.strip()
        if tag in CDP_EVENT_ALLOWLIST:
            return tag
    return None


def properties_from_custom_fields(custom_fields: dict) -> dict:
    """Merge extras for CDP properties; map consent_* flags to consent_granted."""
    extras = dict(custom_fields)
    granted: list[str] = []
    for key, channel in CONSENT_FIELD_TO_CHANNEL.items():
        if key not in extras:
            continue
        value = extras.pop(key)
        truthy = (
            value.strip().lower() in {"true", "1", "yes"} if isinstance(value, str) else value is True or value == 1
        )
        if truthy and channel not in granted:
            granted.append(channel)
    if granted:
        extras["consent_granted"] = granted
    return extras


def build_track_body(entry) -> dict | None:
    """Build the CDP track payload from a FormEntry. None when no tag is allowlisted."""
    tags = entry.tags or ""
    event = get_event_name(tags)
    if event is None:
        return None

    first_name = entry.first_name or ""
    last_name = entry.last_name or ""
    custom_fields = entry.custom_fields if isinstance(entry.custom_fields, dict) else {}
    extras = properties_from_custom_fields(custom_fields)

    return {
        "event": event,
        "eventId": str(entry.id),
        "source": "breathecode",
        "email": entry.email,
        "phone": entry.phone,
        "traits": {
            "name": f"{first_name} {last_name}".strip(),
            "country": entry.country,
        },
        # custom_fields wins on key clashes; consent_* become consent_granted.
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
            **extras,
        },
    }


def build_identify_body(user, profile=None) -> dict | None:
    """Build CDP IdentifyInput from a User. None without email.

    Matches IdentifyInputSchema: userId, email, phone, anonymousId, traits, source, isTest.
    `profile` is unused; phone is resolved via get_user_phone.
    """
    email = (getattr(user, "email", None) or "").strip()
    if not email:
        return None

    body = {
        "source": "breathecode",
        "userId": str(user.id),
        "email": email,
    }

    if name := f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip():
        body["traits"] = {"name": name}

    phone = (get_user_phone(user) or "").strip()
    if len(phone) >= 3:
        body["phone"] = phone

    return body


def track_form_entry(entry) -> bool:
    """POST the lead to the CDP. Returns False when there is nothing to send."""
    api_key = os.getenv("CDP_API_KEY") or ""
    if not api_key:
        logger.info("CDP_API_KEY is empty, skipping lead track")
        return False

    body = build_track_body(entry)
    if body is None:
        logger.info("FormEntry %s has no allowlisted tag (%r), skipping lead track", entry.id, entry.tags)
        return False

    response = requests.post(
        TRACK_URL,
        json=body,
        headers=_auth_headers(api_key),
        timeout=10,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise CdpTrackError(f"CDP track failed with status {response.status_code}")

    return True


def identify_user(user, profile=None) -> bool:
    """POST the user identity to the CDP. Returns False when there is nothing to send."""
    api_key = os.getenv("CDP_API_KEY") or ""
    if not api_key:
        logger.info("CDP_API_KEY is empty, skipping identify")
        return False

    body = build_identify_body(user, profile=profile)
    if body is None:
        logger.info("User %s has no email, skipping identify", getattr(user, "id", None))
        return False

    response = requests.post(
        IDENTIFY_URL,
        json=body,
        headers=_auth_headers(api_key),
        timeout=10,
    )
    if response.status_code < 200 or response.status_code >= 300:
        raise CdpTrackError(f"CDP identify failed with status {response.status_code}")

    return True
