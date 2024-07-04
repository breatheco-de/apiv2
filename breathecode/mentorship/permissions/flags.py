from breathecode.authenticate.models import User
from breathecode.mentorship.models import MentorshipService
from . import contexts
from breathecode.authenticate.permissions import contexts as authenticate_contexts
from breathecode.admissions.permissions import contexts as admissions_contexts

from breathecode.services import LaunchDarkly

__all__ = ["api"]


class Release:

    @staticmethod
    def enable_consume_mentorships(user: User, mentorship_service: MentorshipService) -> bool:
        ld = LaunchDarkly()

        user_context = authenticate_contexts.user(ld, user)
        mentorship_service_context = contexts.mentorship_service(ld, mentorship_service)
        academy_context = admissions_contexts.academy(ld, mentorship_service.academy)

        context = ld.join_contexts(user_context, mentorship_service_context, academy_context)

        return ld.get("api.release.enable_consume_mentorships", context, False)


class API:
    release = Release()


api = API()
