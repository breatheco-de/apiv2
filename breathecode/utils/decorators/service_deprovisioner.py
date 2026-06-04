from typing import Callable, Dict

from capyc.rest_framework.exceptions import ValidationException

__all__ = ["service_deprovisioner", "get_service_deprovisioner"]

_deprovisioners_registry: Dict[str, Callable] = {}


def service_deprovisioner(service_slug: str):
    """
    Register a function as the deprovision handler for a given service slug.
    Usage:
        @service_deprovisioner("free_monthly_llm_budget")
        def deprovision_free_monthly_llm_budget(user_id: int, source: str, context: dict):
            ...
    Only one handler per service slug is allowed; attempting to register a second
    handler for the same slug will raise a ValidationException.
    """

    def decorator(fn: Callable) -> Callable:
        if service_slug in _deprovisioners_registry:
            raise ValidationException(f"Service deprovisioner for {service_slug} already registered")
        _deprovisioners_registry[service_slug] = fn
        return fn

    return decorator


def get_service_deprovisioner(service_slug: str) -> Callable | None:
    return _deprovisioners_registry.get(service_slug)
