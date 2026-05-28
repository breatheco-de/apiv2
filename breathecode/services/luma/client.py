import hashlib
import hmac
import logging
import time
import traceback
from typing import Optional

import breathecode.services.luma.actions as actions

logger = logging.getLogger(__name__)

SIGNATURE_MAX_AGE_SECONDS = 300


class Luma:
    @staticmethod
    def parse_signature_header(signature_header: str) -> dict[str, str]:
        parts = {}
        for part in signature_header.split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            parts[key.strip()] = value.strip()
        return parts

    @staticmethod
    def verify_webhook_signature(secret: str, signature_header: str, raw_body: bytes) -> bool:
        if not secret or not signature_header:
            return False

        parts = Luma.parse_signature_header(signature_header)
        timestamp = parts.get("t")
        signature = parts.get("v1")
        if not timestamp or not signature:
            return False

        try:
            timestamp_int = int(timestamp)
        except ValueError:
            return False

        if abs(time.time() - timestamp_int) > SIGNATURE_MAX_AGE_SECONDS:
            return False

        signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
        expected = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def add_webhook_to_log(payload: dict, organization_id: str, headers: Optional[dict] = None) -> Optional["LumaWebhook"]:
        from breathecode.events.models import LumaWebhook

        if not payload or not len(payload):
            return None

        webhook = LumaWebhook()
        webhook.type = payload.get("type")
        webhook.organization_id = str(organization_id)
        webhook.payload = payload
        webhook.status = "PENDING"

        if headers:
            webhook.webhook_id = headers.get("Webhook-Id") or headers.get("webhook-id")

        data = payload.get("data") or {}
        if isinstance(data, dict) and data.get("id"):
            webhook.luma_guest_id = data.get("id")

        webhook.save()
        return webhook

    def execute_action(self, luma_webhook_id: int):
        from breathecode.events.models import LumaWebhook, Organization

        webhook = LumaWebhook.objects.filter(id=luma_webhook_id).first()
        if not webhook:
            raise Exception("Invalid webhook")

        if not webhook.type:
            raise Exception("Impossible to determine webhook type")

        organization = Organization.objects.filter(id=webhook.organization_id).first()
        if organization is None:
            message = f"Organization {webhook.organization_id} doesn't exist"
            webhook.status = "ERROR"
            webhook.status_text = message
            webhook.save()
            raise Exception(message)

        action = webhook.type.replace(".", "_")
        payload = webhook.payload or {}

        logger.debug(f"Executing Luma action => {action}")
        if hasattr(actions, action):
            fn = getattr(actions, action)

            try:
                fn(self, webhook, payload, organization)
                webhook.refresh_from_db()
                if webhook.status == "PENDING":
                    webhook.status = "DONE"
                    webhook.status_text = "OK"
                    webhook.save()

            except Exception as e:
                logger.error("Mark Luma action with error")
                webhook.status = "ERROR"
                webhook.status_text = "".join(traceback.format_exception(None, e, e.__traceback__))
                webhook.save()

        else:
            message = f"Action `{action}` is not implemented"
            logger.debug(message)
            webhook.status = "ERROR"
            webhook.status_text = message
            webhook.save()
            raise Exception(message)
