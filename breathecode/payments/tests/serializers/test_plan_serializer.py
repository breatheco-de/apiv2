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

