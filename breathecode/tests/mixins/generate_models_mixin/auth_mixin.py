"""
Collections of mixins used to login in authorize microservice
"""

from breathecode.tests.mixins.date_formatter_mixin import DateFormatterMixin
from breathecode.tests.mixins.headers_mixin import HeadersMixin
from breathecode.tests.mixins.models_mixin import ModelsMixin

from .utils import create_models, get_list, is_valid


class AuthMixin(DateFormatterMixin, HeadersMixin, ModelsMixin):
    """CapacitiesTestCase with auth methods"""

    password = "pass1234"

    def generate_credentials(
        self,
        user=False,
        task=False,
        authenticate=False,
        manual_authenticate=False,
        cohort_user=False,
        slack_team=False,
        group=False,
        permission=False,
        mentor_profile=False,
        consumable=False,
        invoice=False,
        subscription=False,
        bag=False,
        user_setting=False,
        consumption_session=False,
        provisioning_container=False,
        app_user_agreement=False,
        first_party_credentials=False,
        task_watcher=False,
        profile_academy="",
        user_kwargs={},
        group_kwargs={},
        permission_kwargs={},
        models={},
        **kwargs,
    ):
        models = models.copy()

        if not "permission" in models and is_valid(permission):
            kargs = {}
            models["permission"] = create_models(permission, "auth.Permission", **{**kargs, **permission_kwargs})

        if not "group" in models and is_valid(group):
            kargs = {}

            if "permission" in models:
                kargs["permissions"] = get_list(models["permission"])

            models["group"] = create_models(group, "auth.Group", **{**kargs, **group_kwargs})

        if not "user" in models and (
            is_valid(user)
            or is_valid(authenticate)
            or is_valid(profile_academy)
            or is_valid(manual_authenticate)
            or is_valid(cohort_user)
            or is_valid(task)
            or is_valid(slack_team)
            or is_valid(mentor_profile)
            or is_valid(consumable)
            or is_valid(invoice)
            or is_valid(subscription)
            or is_valid(bag)
            or is_valid(user_setting)
            or is_valid(consumption_session)
            or is_valid(provisioning_container)
            or is_valid(app_user_agreement)
            or is_valid(first_party_credentials)
            or is_valid(task_watcher)
        ):
            kargs = {}

            if "group" in models:
                kargs["groups"] = get_list(models["group"])

            if "permission" in models:
                kargs["user_permissions"] = get_list(models["permission"])

            models["user"] = create_models(user, "auth.User", **{**kargs, **user_kwargs})

        if authenticate:
            self.client.force_authenticate(user=models["user"])

        if manual_authenticate:
            from breathecode.authenticate.models import Token

            token = Token.objects.create(user=models["user"])
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        return models
