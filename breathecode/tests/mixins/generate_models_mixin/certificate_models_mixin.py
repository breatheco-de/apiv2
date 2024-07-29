"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from .utils import is_valid, create_models, just_one, get_list


class CertificateModelsMixin(ModelsMixin):
    # TODO: Implement Badge
    user_specialty_token = "9e76a2ab3bd55454c384e0a5cdb5298d17285949"

    def generate_certificate_models(
        self,
        layout_design=False,
        specialty=False,
        syllabus=False,
        user_specialty=False,
        layout_design_slug="",
        user_specialty_preview_url="",
        user_specialty_token="",
        badge=False,
        syllabus_kwargs={},
        badge_kwargs={},
        layout_design_kwargs={},
        user_specialty_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "specialty" in models and (is_valid(specialty) or is_valid(user_specialty)):
            kargs = {}

            if "syllabus" in models or syllabus:
                kargs["syllabus"] = just_one(models["syllabus"])

            models["specialty"] = create_models(specialty, "certificate.Specialty", **{**kargs, **syllabus_kwargs})
        if not "badge" in models and badge:
            kargs = {}

            if "specialty" in models or is_valid(specialty):
                kargs["specialties"] = get_list(["specialty"])

            models["badge"] = create_models(specialty, "certificate.Badge", **{**kargs, **badge_kwargs})

        if not "layout_design" in models and is_valid(layout_design):
            kargs = {"slug": "default"}

            if layout_design_slug:
                kargs["slug"] = layout_design_slug

            models["layout_design"] = create_models(
                layout_design, "certificate.LayoutDesign", **{**kargs, **layout_design_kwargs}
            )

        if not "user_specialty" in models and is_valid(user_specialty):
            kargs = {
                "token": self.user_specialty_token,
                "preview_url": "https://asdasd.com",
            }

            if user_specialty_preview_url:
                kargs["preview_url"] = user_specialty_preview_url

            if user_specialty_token:
                kargs["token"] = user_specialty_token

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "specialty" in models:
                kargs["specialty"] = just_one(models["specialty"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "layout_design" in models:
                kargs["layout"] = just_one(models["layout_design"])

            if "cohort" in models:
                kargs["cohort"] = just_one(models["cohort"])

            models["user_specialty"] = create_models(
                user_specialty, "certificate.UserSpecialty", **{**kargs, **user_specialty_kwargs}
            )

        return models
