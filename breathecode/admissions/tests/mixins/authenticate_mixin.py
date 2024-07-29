"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.authenticate.models import Capability, ProfileAcademy, Role
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from breathecode.tests.mixins import DevelopmentEnvironment, DateFormatterMixin


class AuthenticateMixin(APITestCase, DevelopmentEnvironment, DateFormatterMixin):
    """CapacitiesTestCase with auth methods"""

    def remove_model_state(self, dict):
        result = None
        if dict:
            result = dict.copy()
            del result["_state"]

            # remove any field starting with __ (double underscore) because it is considered private
            without_private_keys = result.copy()
            for key in result:
                print("key", key)
                if "__" in key:
                    del without_private_keys[key]

            return without_private_keys

        return result

    def remove_updated_at(self, dict):
        result = None
        if dict:
            result = dict.copy()
            if "updated_at" in result:
                del result["updated_at"]
        return result

    def remove_dinamics_fields(self, dict):
        return self.remove_updated_at(self.remove_model_state(dict))

    def get_capability(self, id):
        return Capability.objects.filter(id=id).first()

    def get_role(self, id):
        return Role.objects.filter(id=id).first()

    def get_profile_academy(self, id):
        return ProfileAcademy.objects.filter(id=id).first()

    def get_capability_dict(self, id):
        data = Capability.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_role_dict(self, id):
        data = Role.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def get_profile_academy_dict(self, id):
        data = ProfileAcademy.objects.filter(id=id).first()
        return self.remove_dinamics_fields(data.__dict__.copy()) if data else None

    def all_capability_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in Capability.objects.filter()]

    def all_role_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in Role.objects.filter()]

    def all_profile_academy_dict(self):
        return [self.remove_dinamics_fields(data.__dict__.copy()) for data in ProfileAcademy.objects.filter()]

    def generate_credentials(self, profile_academy=False, capability="", role="", models=None, external_models=None):

        if models is None:
            models = {}

        if external_models is None:
            external_models = {}

        self.maxDiff = None
        external_models = external_models.copy()
        models = models.copy()
        models = {}

        # if not 'capability' in models and capability:
        if capability:
            kargs = {
                "slug": capability,
                "description": capability,
            }

            models["capability"] = mixer.blend("authenticate.Capability", **kargs)

        if role:
            kargs = {
                "slug": role,
                "name": role,
            }

            if not "role" in models:
                if capability:
                    kargs["capabilities"] = [models["capability"]]

                models["role"] = mixer.blend("authenticate.Role", **kargs)
            else:
                role = Role.objects.filter(**kargs).first()
                role.capabilities.add(models["capability "])
                role.save()
                # models['role'].capabilities.add(models['capability '])
                # models['role'].save()

        if not "profile_academy" in models and profile_academy:
            kargs = {}

            if "user" in models:
                kargs["user"] = external_models["user"]

            if "certificate" in models:
                kargs["certificate"] = external_models["certificate"]

            if "academy" in models:
                kargs["academy"] = external_models["academy"]

            models["profile_academy"] = mixer.blend("authenticate.ProfileAcademy", **kargs)

        return models
