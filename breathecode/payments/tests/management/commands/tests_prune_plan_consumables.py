from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta
from django.core.management.base import CommandError
from django.utils import timezone

from breathecode.payments.management.commands.prune_plan_consumables import Command
from breathecode.payments.models import Consumable
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


def _create_financing(bc: Breathecode, *, status="ACTIVE", paid=3, total=8, extra_month=True):
    next_payment_at = UTC_NOW + relativedelta(days=24)
    model = bc.database.create(
        academy=1,
        user={"email": "sebasgonz777@gmail.com"},
        plan={
            "slug": "plan-apoyo-profesional-ai-engineering",
            "is_renewable": False,
            "time_of_life": 12,
            "time_of_life_unit": "MONTH",
        },
        plan_financing={
            "monthly_price": 100.0,
            "how_many_installments": total,
            "installments_paid": paid,
            "status": status,
            "next_payment_at": next_payment_at,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "valid_until": UTC_NOW + relativedelta(months=6),
        },
        service={"type": "VOID"},
        service_item={"how_many": 4},
    )
    keep = bc.database.create(
        consumable={
            "how_many": 4,
            "valid_until": next_payment_at,
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=keep.id).update(plan_financing=model.plan_financing)

    extra = None
    if extra_month:
        extra = bc.database.create(
            consumable={
                "how_many": 4,
                "valid_until": next_payment_at + relativedelta(months=1),
                "user_id": model.user.id,
                "service_item_id": model.service_item.id,
            }
        ).consumable
        Consumable.objects.filter(id=extra.id).update(plan_financing=model.plan_financing)

    model.plan_financing.refresh_from_db()
    return model, keep, extra


def test_requires_plan_id_or_slug():
    with pytest.raises(CommandError, match="Pass --plan-id or --plan-slug"):
        Command().handle(
            plan_id=None,
            plan_slug=None,
            email=None,
            plan_financing_id=None,
            yes=True,
        )


def test_unknown_plan_id(database: capy.Database):
    with pytest.raises(CommandError, match="Plan id=999 not found"):
        Command().handle(plan_id=999, plan_slug=None, email=None, plan_financing_id=None, yes=True)


def test_lists_and_deletes_consumables_past_next_payment(bc: Breathecode, capsys):
    model, keep, extra = _create_financing(bc)

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=None,
        yes=True,
    )

    remaining = Consumable.objects.filter(plan_financing=model.plan_financing)
    assert remaining.count() == 1
    assert remaining.get().id == keep.id
    assert not Consumable.objects.filter(id=extra.id).exists()

    output = capsys.readouterr().out
    assert "DELETE" in output
    assert "KEEP" in output
    assert "Deleted 1 consumable(s)." in output


def test_prompt_no_keeps_extras(bc: Breathecode, monkeypatch, capsys):
    model, keep, extra = _create_financing(bc)
    monkeypatch.setattr("builtins.input", MagicMock(return_value="n"))

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=None,
        yes=False,
    )

    assert Consumable.objects.filter(id=keep.id).exists()
    assert Consumable.objects.filter(id=extra.id).exists()
    output = capsys.readouterr().out
    assert "Cancelled" in output


def test_prompt_yes_deletes(bc: Breathecode, monkeypatch):
    model, keep, extra = _create_financing(bc)
    monkeypatch.setattr("builtins.input", MagicMock(return_value="y"))

    Command().handle(
        plan_id=None,
        plan_slug=model.plan.slug,
        email="sebasgonz777@gmail.com",
        plan_financing_id=None,
        yes=False,
    )

    assert Consumable.objects.filter(id=keep.id).exists()
    assert not Consumable.objects.filter(id=extra.id).exists()


def test_skips_fully_paid_financings(bc: Breathecode, capsys):
    model, keep, extra = _create_financing(bc, status="FULLY_PAID", paid=8, total=8)

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=None,
        yes=True,
    )

    assert Consumable.objects.filter(id=keep.id).exists()
    assert Consumable.objects.filter(id=extra.id).exists()
    output = capsys.readouterr().out
    assert "Nothing to delete." in output
    assert "Skipped 1 plan financing" in output


def test_keeps_consumable_on_same_calendar_day_as_next_payment(bc: Breathecode, capsys):
    next_payment_at = UTC_NOW.replace(hour=5, minute=43, second=11, microsecond=0) + relativedelta(days=24)
    model = bc.database.create(
        academy=1,
        user={"email": "sebasgonz777@gmail.com"},
        plan={
            "slug": "plan-apoyo-profesional-ai-engineering",
            "is_renewable": False,
            "time_of_life": 12,
            "time_of_life_unit": "MONTH",
        },
        plan_financing={
            "monthly_price": 100.0,
            "how_many_installments": 8,
            "installments_paid": 3,
            "status": "ACTIVE",
            "next_payment_at": next_payment_at,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "valid_until": UTC_NOW + relativedelta(months=6),
        },
        service={"type": "VOID"},
        service_item={"how_many": 4},
    )
    keep = bc.database.create(
        consumable={
            "how_many": 4,
            "valid_until": next_payment_at + relativedelta(hours=12),
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=keep.id).update(plan_financing=model.plan_financing)

    extra = bc.database.create(
        consumable={
            "how_many": 4,
            "valid_until": next_payment_at + relativedelta(months=1),
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=extra.id).update(plan_financing=model.plan_financing)

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=model.plan_financing.id,
        yes=True,
    )

    assert Consumable.objects.filter(id=keep.id).exists()
    assert not Consumable.objects.filter(id=extra.id).exists()
    output = capsys.readouterr().out
    assert "KEEP" in output
    assert "DELETE" in output


def test_keeps_consumable_on_grace_day_after_next_payment(bc: Breathecode, capsys):
    next_payment_at = UTC_NOW.replace(hour=5, minute=43, second=11, microsecond=0) + relativedelta(days=24)
    grace_day = next_payment_at + relativedelta(days=1)
    model = bc.database.create(
        academy=1,
        user={"email": "sebasgonz777@gmail.com"},
        plan={
            "slug": "plan-apoyo-profesional-ai-engineering",
            "is_renewable": False,
            "time_of_life": 12,
            "time_of_life_unit": "MONTH",
        },
        plan_financing={
            "monthly_price": 100.0,
            "how_many_installments": 8,
            "installments_paid": 3,
            "status": "ACTIVE",
            "next_payment_at": next_payment_at,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "valid_until": UTC_NOW + relativedelta(months=6),
        },
        service={"type": "VOID"},
        service_item={"how_many": 4},
    )
    keep_grace = bc.database.create(
        consumable={
            "how_many": 1,
            "valid_until": grace_day,
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=keep_grace.id).update(plan_financing=model.plan_financing)

    extra = bc.database.create(
        consumable={
            "how_many": 4,
            "valid_until": next_payment_at + relativedelta(months=1),
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=extra.id).update(plan_financing=model.plan_financing)

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=model.plan_financing.id,
        yes=True,
    )

    assert Consumable.objects.filter(id=keep_grace.id).exists()
    assert not Consumable.objects.filter(id=extra.id).exists()
    output = capsys.readouterr().out
    assert "KEEP" in output
    assert f"id={keep_grace.id} service=" in output
    assert "DELETE" in output


def test_excludes_expired_consumables_from_list(bc: Breathecode, capsys):
    next_payment_at = UTC_NOW + relativedelta(days=24)
    model = bc.database.create(
        academy=1,
        user={"email": "sebasgonz777@gmail.com"},
        plan={
            "slug": "plan-apoyo-profesional-ai-engineering",
            "is_renewable": False,
            "time_of_life": 12,
            "time_of_life_unit": "MONTH",
        },
        plan_financing={
            "monthly_price": 100.0,
            "how_many_installments": 8,
            "installments_paid": 3,
            "status": "ACTIVE",
            "next_payment_at": next_payment_at,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "valid_until": UTC_NOW + relativedelta(months=6),
        },
        service={"type": "VOID"},
        service_item={"how_many": 4},
    )
    expired = bc.database.create(
        consumable={
            "how_many": 4,
            "valid_until": UTC_NOW - relativedelta(days=10),
            "user_id": model.user.id,
            "service_item_id": model.service_item.id,
        }
    ).consumable
    Consumable.objects.filter(id=expired.id).update(plan_financing=model.plan_financing)

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=model.plan_financing.id,
        yes=True,
    )

    assert Consumable.objects.filter(id=expired.id).exists()
    output = capsys.readouterr().out
    assert f"id={expired.id} service=" not in output
    assert "Skipped 1 expired consumable(s)" in output
    assert "Nothing to delete." in output


def test_nothing_to_delete_when_all_within_period(bc: Breathecode, capsys):
    model, keep, extra = _create_financing(bc, extra_month=False)
    assert extra is None

    Command().handle(
        plan_id=model.plan.id,
        plan_slug=None,
        email=None,
        plan_financing_id=model.plan_financing.id,
        yes=True,
    )

    assert Consumable.objects.filter(id=keep.id).exists()
    output = capsys.readouterr().out
    assert "Nothing to delete." in output
    assert "KEEP" in output
