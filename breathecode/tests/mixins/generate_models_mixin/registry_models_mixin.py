"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class RegistryModelsMixin(ModelsMixin):

    def generate_registry_models(
        self,
        asset_technology=False,
        asset_category=False,
        keyword_cluster=False,
        asset_keyword=False,
        asset=False,
        asset_image=False,
        asset_alias=False,
        asset_comment=False,
        asset_error_log=False,
        models={},
        **kwargs
    ):
        models = models.copy()

        if not "asset_technology" in models and is_valid(asset_technology):
            kargs = {}

            models["asset_technology"] = create_models(asset_technology, "registry.AssetTechnology", **kargs)

        if not "asset_category" in models and is_valid(asset_category):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["asset_category"] = create_models(asset_category, "registry.AssetCategory", **kargs)

        if not "keyword_cluster" in models and is_valid(keyword_cluster):
            kargs = {}

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["keyword_cluster"] = create_models(keyword_cluster, "registry.KeywordCluster", **kargs)

        if not "asset_keyword" in models and is_valid(asset_keyword):
            kargs = {}

            if "keyword_cluster" in models:
                kargs["cluster"] = just_one(models["keyword_cluster"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["asset_keyword"] = create_models(asset_keyword, "registry.AssetKeyword", **kargs)

        if not "asset" in models and (is_valid(asset) or is_valid(asset_alias) or is_valid(asset_comment)):
            kargs = {
                "all_translations": [],
            }

            if "asset_technology" in models:
                kargs["technologies"] = get_list(models["asset_technology"])

            if "asset_keyword" in models:
                kargs["seo_keywords"] = get_list(models["asset_keyword"])

            if "asset_category" in models:
                kargs["category"] = just_one(models["asset_category"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            models["asset"] = create_models(asset, "registry.Asset", **kargs)

        if "asset_technology" in models and "asset" in models:
            technologies = models["asset_technology"]
            if not isinstance(technologies, list):
                technologies = [models["asset_technology"]]
            for instance in technologies:
                instance.featured_asset = just_one(models["asset"])
                instance.save()

        if not "asset_alias" in models and is_valid(asset_alias):
            kargs = {}

            if "asset" in models:
                kargs["asset"] = just_one(models["asset"])

            models["asset_alias"] = create_models(asset_alias, "registry.AssetAlias", **kargs)

        if not "asset_comment" in models and is_valid(asset_comment):
            kargs = {}

            if "asset" in models:
                kargs["asset"] = just_one(models["asset"])

            if "author" in models:
                kargs["user"] = just_one(models["user"])

            models["asset_comment"] = create_models(asset_comment, "registry.AssetComment", **kargs)

        if not "asset_error_log" in models and is_valid(asset_error_log):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "asset" in models:
                kargs["asset"] = just_one(models["asset"])

            models["asset_error_log"] = create_models(asset_error_log, "registry.AssetErrorLog", **kargs)

        if not "asset_image" in models and is_valid(asset_image):
            kargs = {}
            if "asset" in models:
                kargs["assets"] = get_list(models["asset"])

            models["asset_image"] = create_models(asset_image, "registry.AssetImage", **kargs)

        return models
