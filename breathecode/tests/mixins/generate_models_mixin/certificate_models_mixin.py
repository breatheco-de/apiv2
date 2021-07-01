"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.certificate.models import Badge, LayoutDesign, Specialty, UserSpecialty
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer


class CertificateModelsMixin(ModelsMixin):
    # TODO: Implement Badge
    user_specialty_token = '9e76a2ab3bd55454c384e0a5cdb5298d17285949'

    def generate_certificate_models(self,
                                    layout_design=False,
                                    specialty=False,
                                    certificate=False,
                                    user_specialty=False,
                                    layout_design_slug='',
                                    user_specialty_preview_url='',
                                    user_specialty_token='',
                                    badge=False,
                                    specialty_kwargs={},
                                    badge_kwargs={},
                                    layout_design_kwargs={},
                                    user_specialty_kwargs={},
                                    models={},
                                    **kwargs):
        """Generate models"""
        models = models.copy()

        if not 'specialty' in models and specialty:
            kargs = {}

            if 'certificate' in models or certificate:
                kargs['certificate'] = models['certificate']

            kargs = {**kargs, **specialty_kwargs}
            models['specialty'] = mixer.blend('certificate.Specialty', **kargs)

        if not 'badge' in models and badge:
            kargs = {}

            if 'specialty' in models or specialty:
                kargs['specialties'] = [models['specialty']]

            kargs = {**kargs, **badge_kwargs}
            models['badge'] = mixer.blend('certificate.Badge', **kargs)

        if not 'layout_design' in models and layout_design:
            kargs = {'slug': 'default'}

            if layout_design_slug:
                kargs['slug'] = layout_design_slug

            kargs = {**kargs, **layout_design_kwargs}
            models['layout_design'] = mixer.blend('certificate.LayoutDesign',
                                                  **kargs)

        if not 'user_specialty' in models and user_specialty:
            kargs = {
                'token': self.user_specialty_token,
                'preview_url': 'https://asdasd.com',
            }

            if user_specialty_preview_url:
                kargs['preview_url'] = user_specialty_preview_url

            if user_specialty_token:
                kargs['token'] = user_specialty_token

            if 'user' in models:
                kargs['user'] = models['user']

            if 'specialty' in models:
                kargs['specialty'] = models['specialty']

            if 'academy' in models:
                kargs['academy'] = models['academy']

            if 'layout_design' in models:
                kargs['layout'] = models['layout_design']

            if 'cohort' in models:
                kargs['cohort'] = models['cohort']

            kargs = {**kargs, **user_specialty_kwargs}
            models['user_specialty'] = mixer.blend('certificate.UserSpecialty',
                                                   **kargs)

        return models
