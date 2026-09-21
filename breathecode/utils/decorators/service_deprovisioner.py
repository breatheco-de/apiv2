from typing import Callable, Dict

from capyc.rest_framework.exceptions import ValidationException

__all__ = [
    "service_deprovisioner",
    "get_service_deprovisioner",
    "get_service_deprovisioner_slugs",
    "service_power_off",
    "get_service_power_off",
    "get_service_power_off_slugs",
]

_deprovisioners_registry: Dict[str, Callable] = {}
_power_off_registry: Dict[str, Callable] = {}


def service_deprovisioner(service_slug: str):
    """
    Register a function as the deprovision handler for a given service slug.
    Usage:
        @service_deprovisioner("llm-budget")
        def deprovision_llm_budget(user_id: int, source: str, context: dict):
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


def get_service_deprovisioner_slugs() -> tuple[str, ...]:
    return tuple(_deprovisioners_registry)


def service_power_off(service_slug: str):
    """
    Register an optional soft-off handler for a service slug (e.g. power off a VPS).

    Services without this decorator are skipped at the 80% window and only
    go through ``@service_deprovisioner`` at teardown.
    Only one handler per slug.
    """

    def decorator(fn: Callable) -> Callable:
        if service_slug in _power_off_registry:
            raise ValidationException(f"Service power-off handler for {service_slug} already registered")
        _power_off_registry[service_slug] = fn
        return fn

    return decorator


def get_service_power_off(service_slug: str) -> Callable | None:
    return _power_off_registry.get(service_slug)


def get_service_power_off_slugs() -> tuple[str, ...]:
    return tuple(_power_off_registry)
