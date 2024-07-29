"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class MediaModelsMixin(ModelsMixin):

    def generate_media_models(
        self,
        category=False,
        media=False,
        media_resolution=False,
        category_kwargs={},
        media_kwargs={},
        media_resolution_kwargs={},
        models={},
        **kwargs
    ):
        models = models.copy()

        if not "category" in models and is_valid(category):
            kargs = {}

            models["category"] = create_models(category, "media.Category", **{**kargs, **category_kwargs})

        if not "media" in models and is_valid(media):
            kargs = {}

            if "category" in models:
                kargs["categories"] = get_list(models["category"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["media"] = create_models(media, "media.Media", **{**kargs, **media_kwargs})

        if not "media_resolution" in models and is_valid(media_resolution):
            kargs = {}

            models["media_resolution"] = create_models(
                media_resolution, "media.MediaResolution", **{**kargs, **media_resolution_kwargs}
            )

        return models
