import hashlib
import hmac
import json
import time

LUMA_WEBHOOK_SECRET = "whsec_test_secret"
LUMA_EVENT_ID = "evt-test123"
LUMA_CALENDAR_ID = "cal-123"
LUMA_GUEST_ID = "gst-abc123"


def luma_event_payload(event_id=LUMA_EVENT_ID, calendar_id=LUMA_CALENDAR_ID):
    return {
        "platform": "luma",
        "id": event_id,
        "user_id": "usr-host-1",
        "calendar_id": calendar_id,
        "start_at": "2024-01-01T18:00:00.000Z",
        "duration_interval": "PT2H",
        "end_at": "2024-01-01T20:00:00.000Z",
        "created_at": "2024-01-01T00:00:00.000Z",
        "timezone": "America/New_York",
        "name": "Test Workshop",
        "description": "Test description",
        "description_md": "Test description",
        "geo_address_json": None,
        "coordinate": None,
        "meeting_url": "https://lu.ma/test-workshop",
        "cover_url": "https://cdn.lu.ma/cover.png",
        "url": "https://lu.ma/test-workshop",
        "visibility": "public",
        "feedback_email": {"enabled": False},
        "geo_latitude": None,
        "geo_longitude": None,
        "tags": [],
    }


def luma_guest_data(**overrides):
    data = {
        "id": LUMA_GUEST_ID,
        "user_id": "usr-guest-1",
        "user_email": "john.smith@example.com",
        "user_name": "John Smith",
        "user_first_name": "John",
        "user_last_name": "Smith",
        "approval_status": "approved",
        "check_in_qr_code": "qr-code",
        "eth_address": None,
        "invited_at": None,
        "joined_at": None,
        "phone_number": None,
        "registered_at": "2024-01-01T12:00:00.000Z",
        "registration_answers": [],
        "solana_address": None,
        "utm_source": None,
        "event_tickets": [],
        "custom_source": None,
        "event_ticket_orders": [],
        "event": luma_event_payload(),
    }
    data.update(overrides)
    return data


LUMA_GUEST_REGISTERED = {
    "type": "guest.registered",
    "data": luma_guest_data(),
}

LUMA_GUEST_UPDATED = {
    "type": "guest.updated",
    "data": luma_guest_data(
        checked_in_at="2024-01-01T19:00:00.000Z",
        event_tickets=[{"checked_in_at": "2024-01-01T19:00:00.000Z"}],
    ),
}


def sign_luma_request(secret, payload_dict, timestamp=None):
    body = json.dumps(payload_dict).encode("utf-8")
    timestamp_value = str(int(timestamp or time.time()))
    signed_payload = f"{timestamp_value}.{body.decode('utf-8')}"
    signature = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {
        "Webhook-Signature": f"t={timestamp_value},v1={signature}",
        "Webhook-Id": "wh_evt_test_123",
        "Webhook-Timestamp": timestamp_value,
        "Accept": "text/plain",
        "Content-type": "application/json",
    }
    return body, headers
