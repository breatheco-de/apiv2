import os
from functools import lru_cache

from breathecode.payments.utils import ConsumableType, consumable, service_item

__all__ = ["get_virtual_consumables"]


@lru_cache(maxsize=1)
def get_virtual_consumables() -> list[ConsumableType]:
    if os.getenv("ENV") == "production":
        return [
            consumable(
                service_item=service_item(service=48, unit_type="unit", how_many=-1),
            ),
            consumable(
                service_item=service_item(service=93, unit_type="unit", how_many=-1),
            ),
        ]

    return []
