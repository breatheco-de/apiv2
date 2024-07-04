"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.models_mixin import ModelsMixin
from mixer.backend.django import mixer
from .utils import is_valid, create_models, just_one, get_list


class ProvisioningModelsMixin(ModelsMixin):

    def generate_provisioning_models(
        self,
        provisioning_vendor=False,
        provisioning_vendor_kwargs={},
        provisioning_profile=False,
        provisioning_profile_kwargs={},
        provisioning_machine_types=False,
        provisioning_academy=False,
        provisioning_bill=False,
        provisioning_activity=False,
        provisioning_container=False,
        provisioning_consumption_kind=False,
        provisioning_price=False,
        provisioning_consumption_event=False,
        provisioning_user_consumption=False,
        models={},
        **kwargs
    ):
        models = models.copy()

        if not "provisioning_vendor" in models and (
            is_valid(provisioning_vendor) or is_valid(provisioning_consumption_event)
        ):
            kargs = {}

            models["provisioning_vendor"] = create_models(
                provisioning_vendor, "provisioning.ProvisioningVendor", **{**kargs, **provisioning_vendor_kwargs}
            )

        if not "provisioning_profile" in models and is_valid(provisioning_profile):
            kargs = {}

            if "provisioning_vendor" in models:
                kargs["vendor"] = just_one(models["provisioning_vendor"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "cohort" in models:
                kargs["cohorts"] = get_list(models["cohort"])

            if "profile_academy" in models:
                kargs["members"] = get_list(models["profile_academy"])

            models["provisioning_profile"] = create_models(
                provisioning_profile, "provisioning.ProvisioningProfile", **{**kargs, **provisioning_profile_kwargs}
            )

        if not "provisioning_machine_types" in models and is_valid(provisioning_machine_types):
            kargs = {}

            if "provisioning_vendor" in models:
                kargs["vendor"] = just_one(models["provisioning_vendor"])

            models["provisioning_machine_types"] = create_models(
                provisioning_machine_types, "provisioning.ProvisioningMachineTypes", **kargs
            )

        if not "provisioning_academy" in models and is_valid(provisioning_academy):
            kargs = {}

            if "provisioning_vendor" in models:
                kargs["vendor"] = just_one(models["provisioning_vendor"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "provisioning_machine_types" in models:
                kargs["allowed_machine_types"] = get_list(models["provisioning_machine_types"])

            models["provisioning_academy"] = create_models(
                provisioning_academy, "provisioning.ProvisioningAcademy", **kargs
            )

        if not "provisioning_bill" in models and is_valid(provisioning_bill):
            kargs = {}

            if "provisioning_vendor" in models:
                kargs["vendor"] = just_one(models["provisioning_vendor"])

            if "academy" in models:
                kargs["academy"] = just_one(models["academy"])

            if "provisioning_machine_types" in models:
                kargs["allowed_machine_types"] = get_list(models["provisioning_machine_types"])

            models["provisioning_bill"] = create_models(provisioning_bill, "provisioning.ProvisioningBill", **kargs)

        if not "provisioning_consumption_kind" in models and (
            is_valid(provisioning_consumption_kind) or is_valid(provisioning_user_consumption)
        ):
            kargs = {}

            models["provisioning_consumption_kind"] = create_models(
                provisioning_consumption_kind, "provisioning.ProvisioningConsumptionKind", **kargs
            )

        if not "provisioning_price" in models and (
            is_valid(provisioning_price) or is_valid(provisioning_consumption_event)
        ):
            kargs = {}

            if "currency" in models:
                kargs["currency"] = just_one(models["currency"])

            models["provisioning_price"] = create_models(provisioning_price, "provisioning.ProvisioningPrice", **kargs)

        if not "provisioning_consumption_event" in models and is_valid(provisioning_consumption_event):
            kargs = {}

            if "provisioning_vendor" in models:
                kargs["vendor"] = just_one(models["provisioning_vendor"])

            if "provisioning_price" in models:
                kargs["price"] = just_one(models["provisioning_price"])

            models["provisioning_consumption_event"] = create_models(
                provisioning_consumption_event, "provisioning.ProvisioningConsumptionEvent", **kargs
            )

        if not "provisioning_user_consumption" in models and is_valid(provisioning_user_consumption):
            kargs = {}

            if "provisioning_consumption_kind" in models:
                kargs["kind"] = just_one(models["provisioning_consumption_kind"])

            if "provisioning_bill" in models:
                kargs["bills"] = get_list(models["provisioning_bill"])

            if "provisioning_consumption_event" in models:
                kargs["events"] = get_list(models["provisioning_consumption_event"])

            models["provisioning_user_consumption"] = create_models(
                provisioning_user_consumption, "provisioning.ProvisioningUserConsumption", **kargs
            )

        if not "provisioning_activity" in models and is_valid(provisioning_activity):
            kargs = {}

            if "provisioning_bill" in models:
                kargs["bill"] = just_one(models["provisioning_bill"])

            models["provisioning_activity"] = create_models(
                provisioning_activity, "provisioning.ProvisioningActivity", **kargs
            )

        if not "provisioning_container" in models and is_valid(provisioning_container):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["provisioning_container"] = create_models(
                provisioning_container, "provisioning.ProvisioningContainer", **kargs
            )

        return models
