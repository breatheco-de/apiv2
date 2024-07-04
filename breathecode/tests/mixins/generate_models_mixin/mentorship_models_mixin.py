"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class MentorshipModelsMixin(ModelsMixin):

    def generate_mentorship_models(
        self,
        mentorship_service=False,
        mentor_profile=False,
        mentorship_bill=False,
        mentorship_session=False,
        models={},
        **kwargs
    ):
        models = models.copy()

        if not "mentorship_service" in models and (is_valid(mentorship_service)):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["mentorship_service"] = create_models(mentorship_service, "mentorship.MentorshipService", **kargs)

        if not "mentor_profile" in models and (
            is_valid(mentor_profile) or is_valid(mentorship_bill) or is_valid(mentorship_session)
        ):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "mentorship_service" in models:
                kargs["services"] = get_list(models["mentorship_service"])

            if "syllabus" in models:
                kargs["syllabus"] = get_list(models["syllabus"])

            models["mentor_profile"] = create_models(mentor_profile, "mentorship.MentorProfile", **kargs)

        if not "mentorship_bill" in models and is_valid(mentorship_bill):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "user" in models:
                kargs["reviewer"] = just_one(models["user"])

            if "mentor_profile" in models:
                kargs["mentor"] = just_one(models["mentor_profile"])

            models["mentorship_bill"] = create_models(mentorship_bill, "mentorship.MentorshipBill", **kargs)

        if not "mentorship_session" in models and is_valid(mentorship_session):
            kargs = {}

            if "mentor_profile" in models:
                kargs["mentor"] = just_one(models["mentor_profile"])

            if "user" in models:
                kargs["mentee"] = just_one(models["user"])

            if "mentorship_bill" in models:
                kargs["bill"] = just_one(models["mentorship_bill"])

            if "mentorship_service" in models:
                kargs["service"] = just_one(models["mentorship_service"])

            models["mentorship_session"] = create_models(mentorship_session, "mentorship.MentorshipSession", **kargs)

        return models
