"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer

class MediaModelsMixin(ModelsMixin):
    def generate_media_models(self, category=False, media=False,
            category_kwargs={}, media_kwargs={}, models={}, **kwargs):
        models = models.copy()

        if not 'category' in models and category:
            kargs = {}

            kargs = {**kargs, **category_kwargs}
            models['category'] = mixer.blend('media.Category', **kargs)

        if not 'media' in models and media:
            kargs = {}

            if 'category' in models:
                kargs['categories'] = [models['category']]

            if 'academy' in models:
                kargs['academy'] = models['academy']

            kargs = {**kargs, **media_kwargs}
            print('aaaa', media_kwargs)
            models['media'] = mixer.blend('media.Media', **kargs)

        return models
