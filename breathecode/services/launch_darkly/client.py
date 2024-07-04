import logging, os
import re
from typing import Any
import ldclient
from ldclient.config import Config
from ldclient import Context, LDClient

logger = logging.getLogger(__name__)

__all__ = ["LaunchDarkly"]

clients: dict[str, LDClient] = {}


# docs https://docs.launchdarkly.com/sdk/server-side/python/migration-7-to-8
class LaunchDarkly:
    client: LDClient

    def __init__(self, api_key=None):
        api_key = api_key or os.getenv("LAUNCH_DARKLY_API_KEY")

        if api_key not in clients:
            config = Config(api_key)
            ldclient.set_config(config)
            clients[api_key] = ldclient.get()

        self.client = clients[api_key]

    def get(self, key, context, default=None) -> Any:
        return self.client.variation(key, context, default)

    def get_evaluation_reason(self, key, context, default=None) -> Any:
        return self.client.variation_detail(key, context, default)

    def _validate_key(self, key):
        if not re.findall(r"^[a-zA-Z0-9_\-\.]+$", key):
            raise ValueError(
                "The chosen key is invalid, it just must incluse letters, numbers, " "underscore, dash and dot"
            )

    def context(self, key: str, name: str, kind: str, value: dict) -> Context:
        self._validate_key(key)
        self._validate_key(kind)

        context = Context.builder(key).name(name)

        for x in value:
            context = context.set(x, value[x])

        return context.kind(kind).build()

    def join_contexts(self, *contexts: Context):
        return Context.create_multi(*contexts)
