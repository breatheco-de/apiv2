from breathecode.authenticate.models import User
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.admissions.permissions import contexts as admissions_contexts
from breathecode.events.models import Event
from . import contexts

from breathecode.services import LaunchDarkly

__all__ = ['api']


class Release:

    @staticmethod
    def enable_consume_live_classes(user: User) -> bool:
        ld = LaunchDarkly()
        user_context = authenticate_contexts.user(ld, user)
        return ld.get('api.release.enable_consume_live_classes', user_context, False)

    @staticmethod
    def enable_consume_live_events(user: User, event: Event) -> bool:
        ld = LaunchDarkly()
        user_context = authenticate_contexts.user(ld, user)
        event_context = contexts.event(ld, event)
        event_type_context = contexts.event_type(ld, event.event_type)
        academy_context = admissions_contexts.academy(ld, event.academy)

        context = ld.join_contexts(user_context, event_context, event_type_context, academy_context)

        return ld.get('api.release.enable_consume_live_events', context, False)


class API:
    release = Release()


api = API()
