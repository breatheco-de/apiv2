"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins import DateFormatterMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid, just_one


class LinkedServicesMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""

    password = "pass1234"

    def generate_linked_services_models(
        self,
        scope=False,
        app=False,
        app_user_agreement=False,
        optional_scope_set=False,
        legacy_key=False,
        app_required_scope=False,
        app_optional_scope=False,
        first_party_webhook_log=False,
        first_party_credentials=False,
        models={},
        **kwargs
    ):
        models = models.copy()

        if not "scope" in models and (is_valid(scope) or is_valid(app_required_scope) or is_valid(app_optional_scope)):
            kargs = {}

            models["scope"] = create_models(scope, "linked_services.Scope", **kargs)

        if not "app" in models and (
            is_valid(app)
            or is_valid(app_user_agreement)
            or is_valid(legacy_key)
            or is_valid(app_required_scope)
            or is_valid(app_optional_scope)
            or is_valid(first_party_webhook_log)
        ):
            kargs = {
                "public_key": None,
                "private_key": "",
            }

            models["app"] = create_models(app, "linked_services.App", **kargs)

        if not "app_required_scope" in models and is_valid(app_required_scope):
            kargs = {}

            if "app" in models:
                kargs["app"] = just_one(models["app"])

            if "scope" in models:
                kargs["scope"] = just_one(models["scope"])

            models["app_required_scope"] = create_models(
                app_required_scope, "linked_services.AppRequiredScope", **kargs
            )

        if not "app_optional_scope" in models and is_valid(app_optional_scope):
            kargs = {}

            if "app" in models:
                kargs["app"] = just_one(models["app"])

            if "scope" in models:
                kargs["scope"] = just_one(models["scope"])

            models["app_optional_scope"] = create_models(
                app_optional_scope, "linked_services.AppOptionalScope", **kargs
            )

        if not "optional_scope_set" in models and (is_valid(optional_scope_set) or is_valid(app_user_agreement)):
            kargs = {}

            if "scope" in models:
                kargs["optional_scopes"] = get_list(models["scope"])

            models["optional_scope_set"] = create_models(
                optional_scope_set, "linked_services.OptionalScopeSet", **kargs
            )

        if not "app_user_agreement" in models and is_valid(app_user_agreement):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            if "app" in models:
                kargs["app"] = just_one(models["app"])

            if "optional_scope_set" in models:
                kargs["optional_scope_set"] = just_one(models["optional_scope_set"])

            models["app_user_agreement"] = create_models(
                app_user_agreement, "linked_services.AppUserAgreement", **kargs
            )

        if not "legacy_key" in models and is_valid(legacy_key):
            kargs = {}

            if "app" in models:
                kargs["app"] = just_one(models["app"])

            models["legacy_key"] = create_models(legacy_key, "linked_services.LegacyKey", **kargs)

        if not "first_party_credentials" in models and is_valid(first_party_credentials):
            kargs = {}

            if "user" in models:
                kargs["user"] = just_one(models["user"])

            models["first_party_credentials"] = create_models(
                first_party_credentials, "linked_services.FirstPartyCredentials", **kargs
            )

        if not "first_party_webhook_log" in models and is_valid(first_party_webhook_log):
            kargs = {}

            if "app" in models:
                kargs["app"] = just_one(models["app"])

            models["first_party_webhook_log"] = create_models(
                first_party_webhook_log, "linked_services.FirstPartyWebhookLog", **kargs
            )

        return models
