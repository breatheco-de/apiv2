import logging
import traceback

import breathecode.services.learnpack.actions as actions
from breathecode.assignments.models import LearnPackWebhook

logger = logging.getLogger(__name__)


class LearnPack:
    headers = {}

    def has_error(self):
        # {
        #     "error": "VENUE_AND_ONLINE",
        #     "error_description": "You cannot both specify a venue and set online_event",
        #     "status_code": 400
        # }
        pass

    def execute_action(self, webhook_id: int):
        # wonderful way to fix one poor mocking system
        from django.contrib.auth.models import User

        # example: {
        #  "slug": "16-Random-Colors-Loop",
        #  "telemetry_id": "1v95rc9mymikmtvz",
        #  "user_id": 5043,
        #  "stepPosition": 18,
        #  "event": "open_step",
        #  "data": {}
        # }

        webhook = LearnPackWebhook.objects.filter(id=webhook_id).first()
        if not webhook:
            raise Exception("Invalid webhook")

        try:

            if not webhook.event:
                raise Exception("Impossible to determine learnpack event")

            if not webhook.payload:
                raise Exception("Impossible to retrive webhook payload")

            if "slug" not in webhook.payload:
                raise Exception("Impossible to retrive learnpack exercise slug")

            if "user_id" not in webhook.payload:
                raise Exception("Impossible to retrive learnpack user id")
            else:
                user_id = webhook.payload["user_id"]
                user = User.objects.filter(id=user_id).first()
                if user is None:
                    raise Exception(f"Learnpack student with user id {user_id} not found")
                else:
                    webhook.student = user

            logger.debug(f"Executing => {webhook.event}")
            if not hasattr(actions, webhook.event):
                raise Exception(f"Learnpack telemetry event `{webhook.event}` is not implemented")

            logger.debug("Action found")
            fn = getattr(actions, webhook.event)

            try:
                fn(self, webhook)
                logger.debug("Mark action as done")
                webhook.status = "DONE"
                webhook.status_text = "OK"
                webhook.save()

            except Exception as e:
                logger.error("Mark action with error")

                webhook.status = "ERROR"
                webhook.status_text = str(e) + "\n".join(traceback.format_exception(None, e, e.__traceback__))
                webhook.save()

        except Exception as e:
            webhook.status = "ERROR"
            webhook.status_text = str(e) + "\n".join(traceback.format_exception(None, e, e.__traceback__))
            webhook.save()

            raise e

    @staticmethod
    def add_webhook_to_log(payload: dict):
        """Add one incoming webhook request to log"""

        # prevent circular dependency import between thousand modules previuosly loaded and cached
        if not payload or not len(payload):
            return None

        webhook = LearnPackWebhook()
        is_streaming = "event" in payload

        if is_streaming:
            webhook.event = payload["event"]
        else:
            webhook.event = "batch"

        webhook.is_streaming = is_streaming
        webhook.payload = payload
        webhook.status = "PENDING"
        webhook.save()

        return webhook
