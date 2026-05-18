"""
Tests for deal_update — reservation form of payment via custom_fields
"""
from unittest.mock import MagicMock

import pytest

from breathecode.services.activecampaign.actions.deal_update import deal_update
from breathecode.services.activecampaign.client import acp_ids


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
class TestDealUpdateReservationFormOfPaymentInCustomFields:
    """deal_update stores AC deal custom field 51 only in custom_fields blob."""

    def test_reservation_form_of_payment_in_custom_fields_on_deal_update(self, bc):
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
                "custom_fields": None,
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
        assert entry.custom_fields["51"] == "50€ mayo, 50€ junio"
        assert entry.deal_status == "WON"

    def test_custom_fields_without_51_when_field_absent_in_ac(self, bc):
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
                "custom_fields": None,
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )

        ac_mock = MagicMock()
        ac_mock.get_deal_customfields.return_value = {
            "10": "bootcamp-madrid-2025",
        }

        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert "51" not in entry.custom_fields
        assert entry.deal_status == "WON"
