from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from ..mixins import PaymentsTestCase


class TestTeamAPI(PaymentsTestCase):
    @patch("breathecode.payments.actions.create_team_member_with_invite")
    def test_create_invite_owner_only(self, mock_create):
        model = self.bc.database.create(user=1, academy=1)
        other = self.bc.database.create(user=1)

        subs = self.bc.database.create(subscription={"user": model.user, "academy": model.academy}).subscription
        seat_cons = self.bc.database.create(consumable={"subscription": subs, "user": model.user}).consumable

        url = reverse("payments:academy_subscription_id_team_member", kwargs={"subscription_id": subs.id})

        # not owner
        self.bc.request.set_headers(academy=model.academy.id)
        self.client.force_authenticate(user=other.user)
        res = self.client.post(url, {"seat_consumable_id": seat_cons.id, "email": "x@example.com"}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # owner
        self.client.force_authenticate(user=model.user)
        mock_create.return_value = type("Obj", (), {"id": 1, "token": "t", "status": "PENDING"})
        res = self.client.post(url, {"seat_consumable_id": seat_cons.id, "email": "x@example.com"}, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["invite_token"] == "t"

    @patch("breathecode.payments.actions.bulk_create_team_members_with_invites")
    def test_bulk_invite(self, mock_bulk):
        model = self.bc.database.create(user=1, academy=1)
        subs = self.bc.database.create(subscription={"user": model.user, "academy": model.academy}).subscription
        seat_cons = self.bc.database.create(consumable={"subscription": subs, "user": model.user}).consumable

        url = reverse("payments:academy_subscription_id_team_member_bulk", kwargs={"subscription_id": subs.id})
        self.client.force_authenticate(user=model.user)
        mock_bulk.return_value = {"created": [], "errors": []}
        res = self.client.post(url, {"seat_consumable_id": seat_cons.id, "emails": ["a@example.com"]}, format="json")
        assert res.status_code == status.HTTP_207_MULTI_STATUS
