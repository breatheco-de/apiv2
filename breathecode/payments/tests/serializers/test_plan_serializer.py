import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.payments.models import Plan
from breathecode.payments.serializers import PlanSerializer


def _ensure_list(value):
    return value if isinstance(value, (list, tuple)) else [value]


def test_update_sets_financing_options(database):
    model = database.create(plan=1, financing_option=2)
    plan = model.plan

    options = _ensure_list(model.financing_option)
    plan.financing_options.set(options[:1])

    updated_instance = PlanSerializer().update(plan, {"financing_options": options[1:]})

    assert list(updated_instance.financing_options.order_by("id")) == options[1:]


def test_update_clears_financing_options(database):
    model = database.create(plan=1, financing_option=1)
    plan = model.plan

    option = _ensure_list(model.financing_option)
    plan.financing_options.set(option)

    updated_instance = PlanSerializer().update(plan, {"financing_options": None})

    assert updated_instance.financing_options.count() == 0


def test_create_sets_financing_options(database):
    model = database.create(academy=1, currency=1, financing_option=2)
    options = _ensure_list(model.financing_option)

    data = {
        "slug": "test-plan",
        "title": "Test Plan",
        "currency": model.currency.id,
        "owner": model.academy.id,
        "is_renewable": False,
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "financing_options": [option.id for option in options],
    }

    serializer = PlanSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()

    assert list(instance.financing_options.order_by("id")) == options


def test_create_discontinued_requires_discontinued_reason(database):
    model = database.create(academy=1, currency=1)
    data = {
        "slug": "discontinued-plan",
        "title": "T",
        "currency": model.currency.id,
        "owner": model.academy.id,
        "is_renewable": False,
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "status": Plan.Status.DISCONTINUED,
    }
    serializer = PlanSerializer(data=data)
    with pytest.raises(ValidationException) as exc:
        serializer.is_valid(raise_exception=True)
    assert exc.value.slug == "discontinued-reason-required"


def test_create_discontinued_with_discontinued_reason_ok(database):
    model = database.create(academy=1, currency=1)
    data = {
        "slug": "discontinued-plan-2",
        "title": "T",
        "currency": model.currency.id,
        "owner": model.academy.id,
        "is_renewable": False,
        "time_of_life": 1,
        "time_of_life_unit": "MONTH",
        "status": Plan.Status.DISCONTINUED,
        "discontinued_reason": "Replaced by new catalog",
    }
    serializer = PlanSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    assert instance.status == Plan.Status.DISCONTINUED
    assert instance.discontinued_reason == "Replaced by new catalog"


def test_update_to_discontinued_requires_discontinued_reason(database):
    model = database.create(plan=1, academy=1, currency=1)
    plan = model.plan
    plan.status = Plan.Status.ACTIVE
    plan.save()

    serializer = PlanSerializer(plan, data={"status": Plan.Status.DISCONTINUED}, partial=True)
    with pytest.raises(ValidationException) as exc:
        serializer.is_valid(raise_exception=True)
    assert exc.value.slug == "discontinued-reason-required"

