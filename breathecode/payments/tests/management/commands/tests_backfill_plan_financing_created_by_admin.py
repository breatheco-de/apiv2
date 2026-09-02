from unittest.mock import MagicMock

import capyc.pytest as capy
import pytest
from dateutil.relativedelta import relativedelta
from django.core.management.base import CommandError
from django.utils import timezone

from breathecode.payments import tasks
from breathecode.payments.management.commands import backfill_plan_financing_created_by_admin as backfill_command
from breathecode.payments.management.commands.backfill_plan_financing_created_by_admin import Command
from breathecode.payments.models import Invoice, PlanFinancing
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode

UTC_NOW = timezone.now()

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture(autouse=True)
def patch_charge(request, monkeypatch: pytest.MonkeyPatch):
    delay = MagicMock()
    apply = MagicMock()
    renew = MagicMock()
    run_now = MagicMock()
    monkeypatch.setattr(tasks.charge_plan_financing, "delay", delay)
    monkeypatch.setattr(tasks.charge_plan_financing, "apply", apply)
    monkeypatch.setattr(tasks.renew_plan_financing_consumables, "delay", renew)
    if request.node.name != "test_run_task_now_calls_run_with_task_manager_id":
        monkeypatch.setattr(backfill_command, "run_task_now", run_now)
    monkeypatch.setattr("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    return {"delay": delay, "apply": apply, "renew": renew, "run_now": run_now}


def _create_plan_with_proof(database: capy.Database, *, overdue=True, email="staff@example.com", status="ACTIVE"):
    next_payment_at = UTC_NOW - relativedelta(days=9) if overdue else UTC_NOW + relativedelta(days=20)
    model = database.create(
        academy=1,
        user={"email": email},
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": next_payment_at,
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": status,
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": 1,
            "stripe_id": None,
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    return model


def test_marks_plan_with_proof_and_queues_overdue_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["run_now"].assert_called_once_with(tasks.charge_plan_financing, model.plan_financing.id)
    patch_charge["delay"].assert_not_called()


def test_marks_when_only_a_later_invoice_has_proof(database: capy.Database, patch_charge):
    model = database.create(
        academy=1,
        proof_of_payment=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW + relativedelta(days=20),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 2,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "ch_checkout",
        },
    )
    model.plan_financing.invoices.add(model.invoice)
    model.invoice.proof = None
    model.invoice.save(update_fields=["proof"])

    later = Invoice(
        user=model.invoice.user,
        academy=model.invoice.academy,
        currency=model.invoice.currency,
        bag=model.bag,
        amount=50.0,
        paid_at=UTC_NOW - relativedelta(days=5),
        status="FULFILLED",
        proof=model.proof_of_payment,
    )
    later.save()
    model.plan_financing.invoices.add(later)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_dry_run_does_not_mark_or_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database)

    Command().handle(dry_run=True, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_marks_but_does_not_charge_when_next_payment_is_in_the_future(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, overdue=False)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_skips_checkout_plan_without_proof(database: capy.Database, patch_charge):
    model = database.create(
        academy=1,
        plan={"is_renewable": False},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": UTC_NOW - relativedelta(days=9),
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": "ACTIVE",
            "created_by_admin": False,
        },
        bag={"how_many_installments": 12, "was_delivered": True, "type": "BAG"},
        invoice={
            "paid_at": UTC_NOW - relativedelta(months=2),
            "amount": 100.0,
            "status": "FULFILLED",
            "proof_id": None,
            "stripe_id": "ch_checkout",
        },
    )
    model.plan_financing.invoices.add(model.invoice)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_email_filter_skips_other_users(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, email="staff@example.com")

    Command().handle(dry_run=False, email="other@example.com", plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_marks_expired_plan_but_does_not_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, status=PlanFinancing.Status.EXPIRED)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_marks_payment_issue_and_queues_overdue_charge(database: capy.Database, patch_charge):
    model = _create_plan_with_proof(database, status=PlanFinancing.Status.PAYMENT_ISSUE)

    Command().handle(dry_run=False, email=None, plan_financing_id=None)

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["run_now"].assert_called_once_with(tasks.charge_plan_financing, model.plan_financing.id)
    patch_charge["delay"].assert_not_called()


def _create_financing_for_plan(
    bc: Breathecode,
    *,
    slug,
    overdue=True,
    status="ACTIVE",
    created_by_admin=False,
    email="staff@example.com",
    months_overdue=2,
):
    next_payment_at = UTC_NOW - relativedelta(months=months_overdue) if overdue else UTC_NOW + relativedelta(days=20)
    return bc.database.create(
        academy=1,
        user={"email": email},
        plan={"slug": slug, "is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"},
        plan_financing={
            "valid_until": UTC_NOW + relativedelta(months=6),
            "next_payment_at": next_payment_at,
            "monthly_price": 100.0,
            "how_many_installments": 12,
            "installments_paid": 1,
            "plan_expires_at": UTC_NOW + relativedelta(months=12),
            "status": status,
            "created_by_admin": created_by_admin,
        },
    )


def test_plans_flag_rejects_empty_value():
    with pytest.raises(CommandError, match="--plans cannot be empty"):
        Command().handle(dry_run=False, email=None, plan_financing_id=None, plans=" , ")


def test_plans_flag_rejects_unknown_slug(bc: Breathecode):
    bc.database.create(
        plan={"slug": "ai-engineering", "is_renewable": False, "time_of_life": 1, "time_of_life_unit": "MONTH"}
    )

    with pytest.raises(CommandError, match="Unknown plan slug\\(s\\): ai-fluency"):
        Command().handle(
            dry_run=False,
            email=None,
            plan_financing_id=None,
            plans="ai-engineering,ai-fluency",
        )


def test_plans_flag_marks_financings_without_proof(bc: Breathecode, patch_charge):
    matching = _create_financing_for_plan(bc, slug="ai-engineering", overdue=False)
    other = _create_financing_for_plan(bc, slug="other-plan", overdue=False)

    Command().handle(dry_run=False, email=None, plan_financing_id=None, plans="ai-engineering")

    matching.plan_financing.refresh_from_db()
    other.plan_financing.refresh_from_db()
    assert matching.plan_financing.created_by_admin is True
    assert other.plan_financing.created_by_admin is False
    patch_charge["delay"].assert_not_called()
    patch_charge["apply"].assert_not_called()
    patch_charge["renew"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_plans_flag_marks_comma_separated_slugs(bc: Breathecode, patch_charge):
    first = _create_financing_for_plan(bc, slug="ai-engineering", overdue=False)
    second = _create_financing_for_plan(bc, slug="ai-fluency", overdue=False)

    Command().handle(dry_run=False, email=None, plan_financing_id=None, plans="ai-engineering,ai-fluency")

    first.plan_financing.refresh_from_db()
    second.plan_financing.refresh_from_db()
    assert first.plan_financing.created_by_admin is True
    assert second.plan_financing.created_by_admin is True


def test_plans_flag_does_not_charge_payment_issue(bc: Breathecode, patch_charge):
    model = _create_financing_for_plan(
        bc,
        slug="ai-engineering",
        status=PlanFinancing.Status.PAYMENT_ISSUE,
    )

    Command().handle(dry_run=False, email=None, plan_financing_id=None, plans="ai-engineering")

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    patch_charge["apply"].assert_not_called()
    patch_charge["delay"].assert_not_called()
    patch_charge["run_now"].assert_not_called()


def test_plans_flag_catches_up_active_overdue_until_next_payment_in_future(bc: Breathecode, patch_charge):
    model = _create_financing_for_plan(bc, slug="ai-engineering", months_overdue=2)

    def advance(celery_task, plan_financing_id):
        if celery_task is not tasks.charge_plan_financing:
            return
        plan_financing = PlanFinancing.objects.get(id=plan_financing_id)
        plan_financing.next_payment_at = plan_financing.next_payment_at + relativedelta(months=1)
        plan_financing.installments_paid = (plan_financing.installments_paid or 0) + 1
        plan_financing.save(update_fields=["next_payment_at", "installments_paid"])

    patch_charge["run_now"].side_effect = advance

    Command().handle(dry_run=False, email=None, plan_financing_id=None, plans="ai-engineering")

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is True
    assert model.plan_financing.next_payment_at > UTC_NOW
    charge_calls = [
        call for call in patch_charge["run_now"].call_args_list if call.args[0] is tasks.charge_plan_financing
    ]
    renew_calls = [
        call
        for call in patch_charge["run_now"].call_args_list
        if call.args[0] is tasks.renew_plan_financing_consumables
    ]
    assert len(charge_calls) == 3
    assert len(renew_calls) == 1
    patch_charge["apply"].assert_not_called()
    patch_charge["delay"].assert_not_called()


def test_plans_flag_dry_run_does_not_mark_or_charge(bc: Breathecode, patch_charge, capsys):
    model = _create_financing_for_plan(bc, slug="ai-engineering")

    Command().handle(dry_run=True, email=None, plan_financing_id=None, plans="ai-engineering")

    model.plan_financing.refresh_from_db()
    assert model.plan_financing.created_by_admin is False
    patch_charge["apply"].assert_not_called()
    patch_charge["run_now"].assert_not_called()
    output = capsys.readouterr().out
    assert "Would mark 1 plan financing(s) as created_by_admin; would charge 1." in output
    assert "Emails to charge (1):" in output
    assert f"id={model.plan_financing.id} {model.user.email}" in output
    assert "mark=yes" in output


def test_plans_flag_dry_run_skips_already_marked_when_not_charging(bc: Breathecode, patch_charge, capsys):
    model = _create_financing_for_plan(bc, slug="ai-engineering", overdue=False, created_by_admin=True)

    Command().handle(dry_run=True, email=None, plan_financing_id=None, plans="ai-engineering")

    output = capsys.readouterr().out
    assert f"id={model.plan_financing.id}" not in output
    assert "Would mark 0 plan financing(s) as created_by_admin; would charge 0." in output
    assert "Emails to charge" not in output


def test_plans_flag_dry_run_lists_already_marked_only_when_charging(bc: Breathecode, patch_charge, capsys):
    model = _create_financing_for_plan(bc, slug="ai-engineering", created_by_admin=True)

    Command().handle(dry_run=True, email=None, plan_financing_id=None, plans="ai-engineering")

    output = capsys.readouterr().out
    assert f"id={model.plan_financing.id} {model.user.email}" in output
    assert "mark=no" in output
    assert "charge=yes" in output
    assert "Would mark 0 plan financing(s) as created_by_admin; would charge 1." in output
    assert "Emails to charge (1):" in output


def test_run_task_now_calls_run_with_task_manager_id(db):
    run = MagicMock()

    class FakeTask:
        __module__ = "breathecode.payments.tasks"
        __name__ = "charge_plan_financing"

    celery_task = FakeTask()
    celery_task.run = run
    task_manager = backfill_command.run_task_now(celery_task, 42)

    run.assert_called_once_with(42, task_manager_id=task_manager.id)
    task_manager.refresh_from_db()
    assert task_manager.task_name == "charge_plan_financing"
    assert task_manager.arguments["args"] == [42]
