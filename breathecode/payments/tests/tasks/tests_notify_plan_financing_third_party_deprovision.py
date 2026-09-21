from __future__ import annotations

import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from breathecode.payments.models import PlanFinancing
from breathecode.payments.tasks import (
    _third_party_deprovision_notice_copy,
    notify_plan_financing_third_party_deprovision,
)
from breathecode.provisioning.actions import format_deprovision_service_labels


def test_format_deprovision_service_labels_one():
    assert format_deprovision_service_labels([SimpleNamespace(slug="vps_server")]) == "VPS"


def test_format_deprovision_service_labels_two_en():
    services = [SimpleNamespace(slug="vps_server"), SimpleNamespace(slug="github-copilot")]
    assert format_deprovision_service_labels(services, "en") == "VPS and Copilot"


def test_format_deprovision_service_labels_two_es():
    services = [SimpleNamespace(slug="llm-budget"), SimpleNamespace(slug="vps_server")]
    assert format_deprovision_service_labels(services, "es") == "LLM y VPS"


def test_format_deprovision_service_labels_three_en():
    services = [
        SimpleNamespace(slug="vps_server"),
        SimpleNamespace(slug="llm-budget"),
        SimpleNamespace(slug="github-copilot"),
    ]
    assert format_deprovision_service_labels(services, "en") == "VPS, LLM and Copilot"


@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
def test_notice_copy_lists_power_off_and_teardown_only_services():
    vps = SimpleNamespace(id=1, slug="vps_server")
    llm = SimpleNamespace(id=2, slug="llm-budget")
    copilot = SimpleNamespace(id=3, slug="github-copilot")
    subject, message = _third_party_deprovision_notice_copy(
        "QA VPS power-off 80/20",
        [vps, llm, copilot],
        [vps],
        "en",
    )
    assert subject == (
        "Your QA VPS power-off 80/20 plan expired: "
        "the following third-party consumables will be deprovisioned"
    )
    assert "VPS: in 12 days we will power off VPS" in message
    assert "3 days later we will permanently delete VPS" in message
    assert "LLM: in 15 days." in message
    assert "Copilot: in 15 days." in message
    assert "power off LLM" not in message
    assert "power off Copilot" not in message


def _financing_with_vps(bc, *, status: str, plan_expires_at):
    return bc.database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "title": "Full Stack", "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": status,
            "plan_expires_at": plan_expires_at,
            "valid_until": plan_expires_at,
            "next_payment_at": plan_expires_at,
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        service={"type": "VOID", "slug": "vps_server", "consumer": "VPS_SERVER"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )


def _financing_with_llm(bc, *, status: str, plan_expires_at):
    return bc.database.create(
        academy=1,
        user=1,
        plan={"is_renewable": False, "title": "Full Stack", "time_of_life": 12, "time_of_life_unit": "MONTH"},
        plan_financing={
            "status": status,
            "plan_expires_at": plan_expires_at,
            "valid_until": plan_expires_at,
            "next_payment_at": plan_expires_at,
            "how_many_installments": 1,
            "installments_paid": 1,
        },
        service={"type": "VOID", "slug": "llm-budget", "consumer": "LLM_BUDGET"},
        service_item={"how_many": 1},
        plan_service_item=True,
    )


@pytest.mark.django_db
@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
@patch("breathecode.payments.tasks.get_user_settings", return_value=SimpleNamespace(lang="en"))
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_sends_when_fully_paid_and_expiry_reached(mock_send, _mock_settings, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(hours=1),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "message"
    assert args[1] == model.user.email
    assert "VPS" in args[2]["MESSAGE"]
    assert "plan expired" in args[2]["SUBJECT"]
    assert "third-party consumables will be deprovisioned" in args[2]["SUBJECT"]
    assert "powered off in 12 days" not in args[2]["SUBJECT"]
    assert "Copilot" not in args[2]["SUBJECT"]
    assert "LLM" not in args[2]["MESSAGE"]
    assert "<li>" in args[2]["MESSAGE"]
    assert "VPS: in 12 days we will power off VPS" in args[2]["MESSAGE"]
    assert "3 days later we will permanently delete VPS" in args[2]["MESSAGE"]
    assert kwargs["academy"] == model.academy


@pytest.mark.django_db
@patch("breathecode.payments.tasks.get_user_settings", return_value=SimpleNamespace(lang="en"))
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_sends_when_grace_window_already_over(mock_send, _mock_settings, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(days=20),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[1] == model.user.email


@pytest.mark.django_db
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_skips_when_not_fully_paid(mock_send, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.ACTIVE,
        plan_expires_at=timezone.now() - timedelta(hours=1),
    )

    notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_skips_when_expiry_is_still_in_the_future(mock_send, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() + timedelta(days=10),
    )

    notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_not_called()


@pytest.mark.django_db
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
@patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=None)
def test_skips_without_deprovisioner(_mock_get_deprovisioner, mock_send, bc):
    model = _financing_with_vps(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(hours=1),
    )

    notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_not_called()


@pytest.mark.django_db
@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
@patch("breathecode.payments.tasks.get_user_settings", return_value=SimpleNamespace(lang="en"))
@patch("breathecode.payments.tasks.notify_actions.send_email_message")
def test_llm_only_mentions_delete_not_power_off_split(mock_send, _mock_settings, bc):
    model = _financing_with_llm(
        bc,
        status=PlanFinancing.Status.FULLY_PAID,
        plan_expires_at=timezone.now() - timedelta(hours=1),
    )

    with patch("breathecode.provisioning.actions.get_service_deprovisioner", return_value=lambda **kwargs: None):
        notify_plan_financing_third_party_deprovision(model.plan_financing.id)

    mock_send.assert_called_once()
    payload = mock_send.call_args.args[2]
    assert "third-party consumables will be deprovisioned" in payload["SUBJECT"]
    assert "LLM: in 15 days." in payload["MESSAGE"]
    assert "power off" not in payload["MESSAGE"]
