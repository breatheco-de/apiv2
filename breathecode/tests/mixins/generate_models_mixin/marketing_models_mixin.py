"""
Collections of mixins used to login in authorize microservice
"""

from mixer.backend.django import mixer

from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class MarketingModelsMixin(ModelsMixin):

    def generate_marketing_models(
        self,
        active_campaign_academy=False,
        automation=False,
        academy=False,
        tag=False,
        contact=False,
        form_entry=False,
        short_link=False,
        user=False,
        academy_alias=False,
        lead_generation_app=False,
        downloadable=False,
        course=False,
        course_translation=False,
        active_campaign_webhook=False,
        active_campaign_academy_kwargs={},
        automation_kwargs={},
        tag_kwargs={},
        academy_alias_kwargs={},
        contact_kwargs={},
        form_entry_kwargs={},
        short_link_kwargs={},
        lead_generation_app_kwargs={},
        downloadable_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "active_campaign_academy" in models and (
            is_valid(active_campaign_academy) or is_valid(active_campaign_webhook)
        ):
            kargs = {}

            if "academy" in models or academy:
                kargs["academy"] = just_one(models["academy"])

            models["active_campaign_academy"] = create_models(
                active_campaign_academy,
                "marketing.ActiveCampaignAcademy",
                **{**kargs, **active_campaign_academy_kwargs}
            )

        if not "automation" in models and is_valid(automation):
            kargs = {}

            if "active_campaign_academy" in models:
                kargs["ac_academy"] = just_one(models["active_campaign_academy"])

            models["automation"] = create_models(automation, "marketing.Automation", **{**kargs, **automation_kwargs})

        if not "downloadable" in models and is_valid(downloadable):
            kargs = {}

            if "academy" in models and is_valid(downloadable):
                kargs["academy"] = just_one(models["academy"])

            if "user" in models and is_valid(downloadable):
                kargs["user"] = just_one(models["user"])

            models["downloadable"] = create_models(
                downloadable, "marketing.Downloadable", **{**kargs, **downloadable_kwargs}
            )

        if not "course" in models and is_valid(course):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "syllabus" in models:
                kargs["syllabus"] = just_one(models["syllabus"])

            models["course"] = create_models(course, "marketing.Course", **kargs)

        if not "course_translation" in models and is_valid(course_translation):
            kargs = {}

            if "course" in models:
                kargs["course"] = just_one(models["course"])

            models["course_translation"] = create_models(course_translation, "marketing.CourseTranslation", **kargs)

        if not "academy_alias" in models and is_valid(academy_alias):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["academy_alias"] = create_models(
                academy_alias, "marketing.AcademyAlias", **{**kargs, **academy_alias_kwargs}
            )

        # OneToOneField
        if "active_campaign_academy" in models and is_valid(active_campaign_academy):
            if "automation" in models:
                models["active_campaign_academy"].event_attendancy_automation = just_one(models["automation"])

            models["active_campaign_academy"].save()

        if not "tag" in models and is_valid(tag):

            kargs = {}

            if "active_campaign_academy" in models:
                kargs["ac_academy"] = just_one(models["active_campaign_academy"])

            if "automation" in models:
                kargs["automation"] = just_one(models["automation"])

            models["tag"] = create_models(tag, "marketing.Tag", **{**kargs, **tag_kwargs})

        if not "contact" in models and is_valid(contact):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["contact"] = create_models(contact, "marketing.Contact", **{**kargs, **contact_kwargs})

        if not "lead_generation_app" in models and is_valid(lead_generation_app):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = models["academy"]

            if "tag" in models:
                kargs["default_tags"] = [models["tag"]]

            if "automation" in models:
                kargs["default_automations"] = [models["automation"]]

            models["lead_generation_app"] = create_models(
                contact, "marketing.LeadGenerationApp", **{**kargs, **lead_generation_app_kwargs}
            )

        if not "form_entry" in models and is_valid(form_entry):
            kargs = {}

            if "contact" in models:
                kargs["contact"] = just_one(models["contact"])

            if "academy" in models or academy:
                kargs["academy"] = just_one(models["academy"])

            if "active_campaign_academy" in models:
                kargs["ac_academy"] = just_one(models["active_campaign_academy"])

            models["form_entry"] = create_models(form_entry, "marketing.FormEntry", **{**kargs, **form_entry_kwargs})

        if not "short_link" in models and is_valid(short_link):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "user" in models:
                kargs["author"] = just_one(models["user"])

            models["short_link"] = create_models(short_link, "marketing.ShortLink", **{**kargs, **short_link_kwargs})

        if not "active_campaign_webhook" in models and is_valid(active_campaign_webhook):
            kargs = {}

            if "active_campaign_academy" in models:
                kargs["ac_academy"] = just_one(models["active_campaign_academy"])

            if "form_entry" in models:
                kargs["form_entry"] = just_one(models["form_entry"])

            if "contact" in models:
                kargs["contact"] = just_one(models["contact"])

            models["active_campaign_webhook"] = create_models(
                active_campaign_webhook, "marketing.ActiveCampaignWebhook", **kargs
            )

        if not "downloadable" in models and is_valid(downloadable):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "user" in models:
                kargs["author"] = just_one(models["user"])

            models["downloadable"] = create_models(
                downloadable, "marketing.Downloadable", **{**kargs, **downloadable_kwargs}
            )

        return models
