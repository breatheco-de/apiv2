from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone as dt_timezone
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
    expires = datetime(2026, 9, 28, 12, 0, tzinfo=dt_timezone.utc)
    subject, message = _third_party_deprovision_notice_copy(
        "QA VPS power-off 80/20",
        [vps, llm, copilot],
        [vps],
        "en",
        expires,
        "UTC",
    )
    assert subject == 'Action required: your "QA VPS power-off 80/20" plan expired'
    assert "text-align:left" in message
    assert "background-color:#fff8e6" in message
    assert 'Your "QA VPS power-off 80/20" plan has expired.' in message
    assert "You will still have access to the course content and learning materials." in message
    assert "Consumables will stop being generated." in message
    assert "In 12 days (October 10, 2026):" in message
    assert "Your server will be turned off (VPS)." in message
    assert "In 15 days (October 13, 2026):" in message
    assert "Your server and all stored data will be permanently deleted (VPS)." in message
    assert "Access to GitHub Copilot will be disabled (Copilot)." in message
    assert "Your AI credits will stop working (LLM)." in message
    assert "we will power off" not in message
    assert "deprovision" not in message.lower()
    assert "<ul>" not in message


@patch.dict(os.environ, {"THIRD_PARTY_DEPROVISION_GRACE_DAYS": "15"})
def test_notice_copy_spanish_uses_action_required_and_calendar_dates():
    vps = SimpleNamespace(id=1, slug="vps_server")
    llm = SimpleNamespace(id=2, slug="llm-budget")
    copilot = SimpleNamespace(id=3, slug="github-copilot")
    expires = datetime(2026, 9, 28, 12, 0, tzinfo=dt_timezone.utc)
    subject, message = _third_party_deprovision_notice_copy(
        "Plan Apoyo Profesional - AI Engineering",
        [vps, llm, copilot],
        [vps],
        "es",
        expires,
        "UTC",
    )
    assert subject == 'Acción requerida: tu plan "Plan Apoyo Profesional - AI Engineering" venció'
    assert 'Tu plan "Plan Apoyo Profesional - AI Engineering" venció.' in message
    assert "Seguirás teniendo acceso al contenido del curso y a los materiales de aprendizaje." in message
    assert "Los consumibles dejarán de generarse." in message
    assert "En 12 días (10 de octubre de 2026):" in message
    assert "Tu servidor se apagará (VPS)." in message
    assert "En 15 días (13 de octubre de 2026):" in message
    assert "se borrarán de forma permanente (VPS)." in message
    assert "Se desactivará GitHub Copilot (Copilot)." in message
    assert "Tus créditos de IA dejarán de funcionar (LLM)." in message


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
    assert args[2]["SUBJECT"].startswith("Action required:")
    assert 'your "Full Stack" plan expired' in args[2]["SUBJECT"]
    assert "third-party consumables" not in args[2]["SUBJECT"]
    assert "Your server will be turned off (VPS)." in args[2]["MESSAGE"]
    assert "permanently deleted" in args[2]["MESSAGE"]
    assert "In 12 days (" in args[2]["MESSAGE"]
    assert "In 15 days (" in args[2]["MESSAGE"]
    assert "text-align:left" in args[2]["MESSAGE"]
    assert "Copilot" not in args[2]["MESSAGE"]
    assert "AI credits" not in args[2]["MESSAGE"]
    assert args[2]["BUTTON"] == "Go to 4Geeks"
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
    assert payload["SUBJECT"].startswith("Action required:")
    assert "Your AI credits will stop working (LLM)." in payload["MESSAGE"]
    assert "In 15 days (" in payload["MESSAGE"]
    assert "turned off" not in payload["MESSAGE"]
    assert "power off" not in payload["MESSAGE"]
