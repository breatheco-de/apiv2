from unittest.mock import MagicMock, patch

import pytest

from breathecode.services.activecampaign.actions.deal_add import deal_add
from breathecode.services.activecampaign.client import acp_ids

DEAL_PAYLOAD = {
    "deal[id]": "999",
    "deal[contactid]": "111",
    "deal[contact_email]": "test@4geeks.com",
    "deal[status]": "0",
    "deal[owner]": "5",
    "deal[owner_firstname]": "Luis",
    "deal[owner_lastname]": "Del Valle",
    "deal[value_raw]": "100.0",
    "deal[currency]": "EUR",
}


@pytest.mark.django_db
@patch("breathecode.marketing.tasks.async_update_deal_custom_fields.delay")
class TestDealAddDoesNotStealFormEntry:

    def test_binds_unbound_form_entry(self, mock_delay, bc):
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
            },
            active_campaign_webhook={"webhook_type": "deal_add", "payload": DEAL_PAYLOAD},
        )

        deal_add(MagicMock(), model.active_campaign_webhook, DEAL_PAYLOAD, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.ac_deal_id == "999"

    def test_does_not_steal_form_entry_bound_to_another_deal(self, mock_delay, bc):
        model = bc.database.create(
            form_entry={
                "email": "pedro@test.com",
                "storage_status": "PERSISTED",
                "deal_status": "WON",
                "ac_deal_id": "360219",
                "ac_contact_id": "299535",
            },
            active_campaign_webhook={"webhook_type": "deal_add", "payload": DEAL_PAYLOAD},
        )
        workshop = dict(DEAL_PAYLOAD)
        workshop["deal[id]"] = "364022"
        workshop["deal[contactid]"] = "299535"
        workshop["deal[contact_email]"] = "pedro@test.com"

        with pytest.raises(Exception, match="Impossible to find formentry"):
            deal_add(MagicMock(), model.active_campaign_webhook, workshop, acp_ids)

        from breathecode.marketing.models import FormEntry

        entry = FormEntry.objects.get(id=model.form_entry.id)
        assert entry.ac_deal_id == "360219"
        assert entry.deal_status == "WON"

    @patch("breathecode.marketing.models.form_entry_won_or_lost.send_robust")
    def test_second_same_status_does_not_fire_again(self, mock_signal, mock_delay, bc):
        payload = dict(DEAL_PAYLOAD)
        payload["deal[status]"] = "1"
        model = bc.database.create(
            form_entry={
                "email": "test@4geeks.com",
                "storage_status": "PERSISTED",
                "deal_status": None,
                "ac_deal_id": None,
                "ac_contact_id": "111",
            },
            active_campaign_webhook={"webhook_type": "deal_add", "payload": payload},
        )

        deal_add(MagicMock(), model.active_campaign_webhook, payload, acp_ids)
        assert mock_signal.call_count == 1
        deal_add(MagicMock(), model.active_campaign_webhook, payload, acp_ids)
        assert mock_signal.call_count == 1
