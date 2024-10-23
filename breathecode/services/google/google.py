__all__ = ["GoogleMeet"]


import base64
import json
import re
from typing import Callable, Literal, TypedDict

from asgiref.sync import async_to_sync
from django.db.models import QuerySet
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.models import CredentialsGoogle, GoogleWebhook

from . import actions

__all__ = ["Google"]


def camel_to_snake(camel: str):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


type WebhookType = Literal["conferenceRecord"] | Literal["participantSession"]


class WebhookData(TypedDict):
    name: str


type WebhookMessage = dict[WebhookType, WebhookData]

type Action = Callable[[str, QuerySet[CredentialsGoogle]], None]


class Google:

    @async_to_sync
    async def run_webhook(self, hook: GoogleWebhook, credentials: QuerySet[CredentialsGoogle]):
        if hook.status == GoogleWebhook.Status.DONE:
            raise AbortTask(f"GoogleWebhook with id {hook.id} was processed")

        decoded_message = base64.b64decode(hook.message).decode("utf-8")
        message: WebhookMessage = json.loads(decoded_message)

        if not message:
            raise AbortTask("Message is empty")

        key = next(iter(message.keys()))

        action = camel_to_snake(key)
        if hasattr(actions, action) is False:
            raise AbortTask(f"Action {action} not found")

        handler: Action = getattr(actions, action)
        name = message[key]["name"]

        hook.type = key

        # loop = asyncio.get_event_loop()
        # asyncio.set_event_loop(loop)
        try:
            await handler(name, credentials)
            hook.status = GoogleWebhook.Status.DONE
            await hook.asave()
            return

        except Exception as e:
            import traceback

            hook.status = GoogleWebhook.Status.ERROR
            hook.status_text = str(e)

            traceback.print_exc()
            await hook.asave()
            raise e

        # finally:
        #     # loop.close()
