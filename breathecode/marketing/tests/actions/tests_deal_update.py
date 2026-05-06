"""
Tests for deal_update actions — update_reservation_form_of_payment
"""
from unittest.mock import MagicMock, patch

import pytest

from breathecode.services.activecampaign.actions.deal_update import (
    deal_update,
    update_reservation_form_of_payment,
)
from breathecode.services.activecampaign.client import acp_ids


# ──────────────────────────────────────────────────────────────────────────────
# Opción 1 — Unit tests de la función pura (sin base de datos)
# ──────────────────────────────────────────────────────────────────────────────


class TestUpdateReservationFormOfPayment:
    """Unit tests for update_reservation_form_of_payment (no DB needed)"""

    def test_field_is_set_when_present(self):
        """El campo se guarda cuando AC devuelve el valor para el ID 51"""
        entry = MagicMock()
        entry.ac_reservation_or_course_form_of_payment = None

        deal_custom_fields = {"51": "50€ mayo, 50€ junio"}

        result = update_reservation_form_of_payment(None, entry, acp_ids, deal_custom_fields)

        assert result.ac_reservation_or_course_form_of_payment == "50€ mayo, 50€ junio"

    def test_field_not_overwritten_when_empty_string(self):
        """Si AC devuelve cadena vacía, el campo no se sobreescribe"""
        entry = MagicMock()
        entry.ac_reservation_or_course_form_of_payment = "valor previo"

        deal_custom_fields = {"51": ""}

        result = update_reservation_form_of_payment(None, entry, acp_ids, deal_custom_fields)

        assert result.ac_reservation_or_course_form_of_payment == "valor previo"

    def test_field_not_overwritten_when_none(self):
        """Si AC devuelve None, el campo no se sobreescribe"""
        entry = MagicMock()
        entry.ac_reservation_or_course_form_of_payment = "valor previo"

        deal_custom_fields = {"51": None}

        result = update_reservation_form_of_payment(None, entry, acp_ids, deal_custom_fields)

        assert result.ac_reservation_or_course_form_of_payment == "valor previo"

    def test_field_unchanged_when_key_absent(self):
        """Si el campo 51 no viene en los custom fields, no se toca el entry"""
        entry = MagicMock()
        entry.ac_reservation_or_course_form_of_payment = "valor previo"

        deal_custom_fields = {"10": "some-cohort"}  # otro campo, sin el 51

        result = update_reservation_form_of_payment(None, entry, acp_ids, deal_custom_fields)

        assert result.ac_reservation_or_course_form_of_payment == "valor previo"


# ──────────────────────────────────────────────────────────────────────────────
# Opción 2 — Simulación del webhook completo con deal_update (con DB)
# ──────────────────────────────────────────────────────────────────────────────


DEAL_PAYLOAD = {
    "deal[id]": "999",
    "deal[contactid]": "111",
    "deal[contact_email]": "test@4geeks.com",
    "deal[status]": "1",  # WON
    "deal[owner]": "5",
    "deal[owner_firstname]": "Luis",
    "deal[owner_lastname]": "Del Valle",
    "deal[value_raw]": "100.0",
    "deal[currency]": "EUR",
}


@pytest.mark.django_db
class TestDealUpdateWebhookSimulation:
    """
    Simula el flujo completo de deal_update:
    AC client mockeado → verifica que ac_reservation_or_course_form_of_payment
    se persiste en el FormEntry.
    """

    def test_reservation_form_of_payment_saved_on_deal_update(self, bc):
        """deal_update guarda el campo cuando AC devuelve el custom field 51"""
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
                "ac_reservation_or_course_form_of_payment": None,
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )

        ac_mock = MagicMock()
        ac_mock.get_deal_customfields.return_value = {
            "51": "50€ mayo, 50€ junio",
            "10": "bootcamp-madrid-2025",
        }

        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.ac_reservation_or_course_form_of_payment == "50€ mayo, 50€ junio"
        assert entry.deal_status == "WON"

    def test_reservation_form_of_payment_not_set_when_field_absent(self, bc):
        """deal_update no falla si AC no devuelve el campo 51"""
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
                "ac_reservation_or_course_form_of_payment": None,
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )

        ac_mock = MagicMock()
        ac_mock.get_deal_customfields.return_value = {
            "10": "bootcamp-madrid-2025",
            # campo 51 ausente a propósito
        }

        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.ac_reservation_or_course_form_of_payment is None
