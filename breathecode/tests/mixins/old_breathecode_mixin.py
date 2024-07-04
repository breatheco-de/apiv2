"""
Cache mixin
"""

import requests
from breathecode.tests.mocks import OLD_BREATHECODE_INSTANCES
from unittest.mock import call
from breathecode.services import SOURCE, CAMPAIGN

__all__ = ["OldBreathecodeMixin"]


class OldBreathecodeMixin:
    """Cache mixin"""

    old_breathecode_host = "https://old.hardcoded.breathecode.url"
    OLD_BREATHECODE_TYPES = ["create_contact", "contact_automations"]

    def __contact_automations_call__(self, model):
        return call(
            "POST",
            f"{self.old_breathecode_host}/api/3/contactAutomations",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Api-Token": model["active_campaign_academy"].ac_key,
            },
            json={
                "contactAutomation": {
                    "contact": 1,
                    "automation": model["automation"].acp_id,
                }
            },
            timeout=3,
        )

    def reset_old_breathecode_calls(self):
        mock = requests.request
        mock.call_args_list = []

    def check_old_breathecode_calls(self, model, types):
        mock = requests.request

        calls = []
        for type in types:
            method = getattr(self, f"__{type}_call__")

            if not method:
                raise Exception(f"Type {type} is not implemented")

            calls.append(method(model))

        assert len(mock.call_args_list) == len(calls)
        for n in range(len(calls)):
            # assert mock.call_args_list[n] == calls[n]
            assert self.assertEqual(mock.call_args_list[n], calls[n])
