import logging
from breathecode.authenticate.models import User
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.admissions.permissions import contexts as admissions_contexts
from breathecode.events.models import Event
from . import contexts

from breathecode.services import LaunchDarkly

__all__ = ["api"]

logger = logging.getLogger(__name__)


class Release:

    @staticmethod
    def enable_consume_live_classes(user: User) -> bool:
        ld = LaunchDarkly()
        user_context = authenticate_contexts.user(ld, user)
        return ld.get("api.release.enable_consume_live_classes", user_context, False)

    @staticmethod
    def enable_consume_live_events(user: User, event: Event) -> bool:
        ld = LaunchDarkly()

        collected_contexts = []

        collected_contexts.append(authenticate_contexts.user(ld, user))
        collected_contexts.append(contexts.event(ld, event))

        if event.event_type:
            collected_contexts.append(contexts.event_type(ld, event.event_type))

        if event.academy:
            collected_contexts.append(admissions_contexts.academy(ld, event.academy))

        context = ld.join_contexts(*collected_contexts)

        return ld.get("api.release.enable_consume_live_events", context, False)


class API:
    release = Release()


api = API()
