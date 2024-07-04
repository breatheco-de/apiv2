"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class CareerModelsMixin(ModelsMixin):

    def generate_career_models(
        self,
        platform=False,
        position=False,
        zyte_project=False,
        spider=False,
        position_alias=False,
        career_tag=False,
        location=False,
        location_alias=False,
        employer=False,
        job=False,
        platform_kwargs={},
        position_kwargs={},
        zyte_project_kwargs={},
        spider_kwargs={},
        position_alias_kwargs={},
        career_tag_kwargs={},
        location_kwargs={},
        location_alias_kwargs={},
        employer_kwargs={},
        job_kwargs={},
        models={},
        **kwargs
    ):
        """Generate models"""
        models = models.copy()

        if not "platform" in models and is_valid(platform):
            kargs = {}

            models["platform"] = create_models(platform, "career.Platform", **{**kargs, **platform_kwargs})

        if not "position" in models and (is_valid(position) or is_valid(spider)):
            kargs = {}

            models["position"] = create_models(position, "career.Position", **{**kargs, **position_kwargs})

        if not "zyte_project" in models and (is_valid(zyte_project) or is_valid(spider)):
            kargs = {}

            if "platform" in models:
                kargs["platform"] = just_one(models["platform"])

            models["zyte_project"] = create_models(
                zyte_project, "career.ZyteProject", **{**kargs, **zyte_project_kwargs}
            )

        if not "spider" in models and is_valid(spider):
            kargs = {}

            if "position" in models:
                kargs["position"] = just_one(models["position"])

            if "zyte_project" in models:
                kargs["zyte_project"] = just_one(models["zyte_project"])

            models["spider"] = create_models(spider, "career.Spider", **{**kargs, **spider_kwargs})

        if not "position_alias" in models and is_valid(position_alias):
            kargs = {}

            if "position" in models:
                kargs["position"] = just_one(models["position"])

            models["position_alias"] = create_models(
                position_alias, "career.PositionAlias", **{**kargs, **position_alias_kwargs}
            )

        if not "career_tag" in models and is_valid(career_tag):
            kargs = {}

            models["career_tag"] = create_models(career_tag, "career.CareerTag", **{**kargs, **career_tag_kwargs})

        if not "location" in models and is_valid(location):
            kargs = {}

            models["location"] = create_models(location, "career.Location", **{**kargs, **location_kwargs})

        if not "location_alias" in models and is_valid(location_alias):
            kargs = {}

            if "location" in models:
                kargs["location"] = just_one(models["location"])

            models["location_alias"] = create_models(
                location_alias, "career.LocationAlias", **{**kargs, **location_alias_kwargs}
            )

        if not "employer" in models and is_valid(employer):
            kargs = {}

            if "location" in models:
                kargs["location"] = just_one(models["location"])

            models["employer"] = create_models(employer, "career.Employer", **{**kargs, **employer_kwargs})

        if not "job" in models and (is_valid(job) or is_valid(employer)):
            kargs = {}

            if "spider" in models:
                kargs["spider"] = just_one(models["spider"])

            if "employer" in models:
                kargs["employer"] = just_one(models["employer"])

            if "position" in models:
                kargs["position"] = just_one(models["position"])

            if "career_tag" in models:
                kargs["career_tag"] = just_one(models["career_tag"])

            if "location" in models:
                kargs["location"] = just_one(models["location"])

            models["job"] = create_models(job, "career.Job", **{**kargs, **job_kwargs})

        return models
