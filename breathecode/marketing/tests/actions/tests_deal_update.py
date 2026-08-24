"""
Tests for deal_update — reservation form of payment via custom_fields
"""
from unittest.mock import MagicMock, patch

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


def _ac_mock():
    ac_mock = MagicMock()
    ac_mock.get_deal_customfields.return_value = {}
    return ac_mock


def _payload(**overrides):
    data = dict(DEAL_PAYLOAD)
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestDealUpdateWonOrLostIdempotency:

    @patch("breathecode.marketing.models.form_entry_won_or_lost.send_robust")
    def test_second_won_update_does_not_fire_signal_again(self, mock_signal, bc):
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )
        ac_mock = _ac_mock()
        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)
        assert mock_signal.call_count == 1

        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)
        assert mock_signal.call_count == 1

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.deal_status == "WON"
        assert entry.ac_deal_id == "999"

    @patch("breathecode.marketing.models.form_entry_won_or_lost.send_robust")
    def test_won_then_lost_fires_signal(self, mock_signal, bc):
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": "999",
                "ac_contact_id": "111",
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )
        ac_mock = _ac_mock()
        deal_update(ac_mock, model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)
        assert mock_signal.call_count == 1

        lost = _payload(**{"deal[status]": "2"})
        deal_update(ac_mock, model.active_campaign_webhook, lost, acp_ids)
        assert mock_signal.call_count == 2

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.deal_status == "LOST"
        assert entry.won_at is None

    def test_does_not_steal_form_entry_bound_to_another_deal(self, bc):
        model = bc.database.create(
            form_entry={
                "email": "pedro@test.com",
                "storage_status": "PERSISTED",
                "deal_status": "WON",
                "ac_deal_id": "360219",
                "ac_contact_id": "299535",
                "course": "ai-engineering",
            },
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )
        workshop = _payload(
            **{
                "deal[id]": "364022",
                "deal[contactid]": "299535",
                "deal[contact_email]": "pedro@test.com",
                "deal[status]": "0",
            }
        )

        with pytest.raises(Exception, match="Impossible to find formentry"):
            deal_update(_ac_mock(), model.active_campaign_webhook, workshop, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.ac_deal_id == "360219"
        assert entry.deal_status == "WON"

    def test_two_courses_won_updates_only_matching_form_entry(self, bc):
        model = bc.database.create(
            form_entry=[
                {
                    "email": "two@test.com",
                    "storage_status": "PERSISTED",
                    "deal_status": None,
                    "ac_deal_id": "100",
                    "ac_contact_id": "50",
                    "course": "full-stack",
                },
                {
                    "email": "two@test.com",
                    "storage_status": "PERSISTED",
                    "deal_status": None,
                    "ac_deal_id": "200",
                    "ac_contact_id": "50",
                    "course": "ai-engineering",
                },
            ],
            active_campaign_webhook={"webhook_type": "deal_update", "payload": DEAL_PAYLOAD},
        )

        payload_b = _payload(
            **{
                "deal[id]": "200",
                "deal[contactid]": "50",
                "deal[contact_email]": "two@test.com",
            }
        )
        deal_update(_ac_mock(), model.active_campaign_webhook, payload_b, acp_ids)

        from breathecode.marketing.models import FormEntry

        fullstack = FormEntry.objects.get(id=model.form_entry[0].id)
        ai = FormEntry.objects.get(id=model.form_entry[1].id)
        assert fullstack.deal_status is None
        assert fullstack.ac_deal_id == "100"
        assert ai.deal_status == "WON"
        assert ai.ac_deal_id == "200"
