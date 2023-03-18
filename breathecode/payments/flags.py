from breathecode.admissions.models import Academy
from breathecode.authenticate.models import User
from breathecode.mentorship.models import MentorshipService
from breathecode.events.models import LiveClass
from breathecode.payments import contexts

from breathecode.services import LaunchDarkly

__all__ = ['api']


class Release:

    @staticmethod
    def enable_consume_live_classes(user: User) -> bool:
        ld = LaunchDarkly()
        user_context = contexts.user(ld, user)
        return ld.get('api.release.enable_consume_live_classes', user_context, False)

    @staticmethod
    def enable_consume_mentorships(user: User, mentorship_service: MentorshipService) -> bool:
        ld = LaunchDarkly()

        user_context = contexts.user(ld, user)
        mentorship_service_context = contexts.mentorship_service(ld, mentorship_service)
        academy_context = contexts.academy(ld, mentorship_service.academy)

        context = ld.join_contexts(user_context, mentorship_service_context, academy_context)

        return ld.get('api.release.enable_consume_mentorships', context, False)


class API:
    release = Release()


api = API()
