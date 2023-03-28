"""
Collections of mixins used to login in authorize microservice
"""
from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class ProvisioningMixin(ModelsMixin):

    def generate_provisioning_models(self,
                                     provisioning_vendor=False,
                                     provisioning_vendor_kwargs={},
                                     provisioning_profile=False,
                                     provisioning_profile_kwargs={},
                                     academy=False,
                                     models={},
                                     **kwargs):
        models = models.copy()

        if not 'academy' in models and is_valid(academy):
            kargs = {}

            models['academy'] = create_models(academy, 'admissions.Academy', **kargs)

        if not 'provisioning_vendor' in models and is_valid(provisioning_vendor):
            kargs = {}

            models['provisioning_vendor'] = create_models(provisioning_vendor,
                                                          'provisioning.ProvisioningVendor', **{
                                                              **kargs,
                                                              **provisioning_vendor_kwargs
                                                          })

        if not 'provisioning_profile' in models and is_valid(provisioning_profile):
            kargs = {}

            if 'provisioning_vendor' in models:
                kargs['vendor'] = just_one(models['provisioning_vendor'])

            if 'academy' in models:
                kargs['academy'] = just_one(models['academy'])

            models['provisioning_profile'] = create_models(provisioning_profile,
                                                           'provisioning.ProvisioningProfile', **{
                                                               **kargs,
                                                               **provisioning_profile_kwargs
                                                           })

        return models
