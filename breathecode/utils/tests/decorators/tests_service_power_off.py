from capyc.rest_framework.exceptions import ValidationException

from breathecode.utils.decorators.service_deprovisioner import (
    get_service_power_off,
    get_service_power_off_slugs,
    service_power_off,
)


def test_registers_and_gets_handler():
    slug = "qa-power-off-registry"

    @service_power_off(slug)
    def _handler(**kwargs):
        return "ok"

    assert get_service_power_off(slug) is _handler
    assert slug in get_service_power_off_slugs()


def test_duplicate_slug_raises():
    slug = "qa-power-off-duplicate"

    @service_power_off(slug)
    def _first(**kwargs):
        return None

    try:

        @service_power_off(slug)
        def _second(**kwargs):
            return None

        raise AssertionError("expected ValidationException")
    except ValidationException:
        pass
