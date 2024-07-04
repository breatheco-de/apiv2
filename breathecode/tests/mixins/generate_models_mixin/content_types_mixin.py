"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.tests.mixins import DateFormatterMixin
from .utils import is_valid, create_models, get_list


class ContentTypesMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""

    def generate_contenttypes_models(self, content_type=False, models={}, **kwargs):
        models = models.copy()

        if not "content_type" in models and is_valid(content_type):
            kargs = {}
            models["content_type"] = create_models(content_type, "contenttypes.ContentType", **kargs)

        return models
