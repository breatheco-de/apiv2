"""
Test /v1/provisioning/academy/bill/<bill_id>/consumptions
"""

from django.urls.base import reverse_lazy
from rest_framework import status

from ..mixins import ProvisioningTestCase

UTC_NOW = None


class AcademyBillConsumptionsTestSuite(ProvisioningTestCase):
    """Test /academy/bill/<bill_id>/consumptions"""

    # When: no auth
    # Then: should return 401
    def test_consumptions_without_auth(self):

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # When: auth and no capability
    # Then: should return 403
    def test_consumptions_without_capability(self):

        model = self.bc.database.create(user=1)
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_provisioning_bill for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # When: bill doesn't exist
    # Then: should return 404
    def test_consumptions__bill_not_found(self):

        model = self.bc.database.create(
            user=1, profile_academy=1, role=1, capability="read_provisioning_bill"
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Provisioning Bill not found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # When: bill exists but belongs to different academy
    # Then: should return 404
    def test_consumptions__bill_wrong_academy(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_bill",
            provisioning_bill=1,
            academy=2,  # Different academy
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Provisioning Bill not found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # When: bill exists with no consumptions
    # Then: should return empty paginated results
    def test_consumptions__no_consumptions(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_bill",
            provisioning_bill=1,
            academy=1,
        )
        self.client.force_authenticate(model.user)

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)

        json = response.json()
        expected = {
            "count": 0,
            "first": None,
            "next": None,
            "previous": None,
            "last": None,
            "results": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # When: bill exists with consumptions
    # Then: should return paginated consumptions ordered by username
    def test_consumptions__with_consumptions(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_bill",
            provisioning_bill=1,
            academy=1,
            provisioning_user_consumption=2,
            provisioning_consumption_kind=1,
        )
        self.client.force_authenticate(model.user)

        # Link consumptions to bill
        for consumption in model.provisioning_user_consumption:
            consumption.bills.add(model.provisioning_bill)
            consumption.save()

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1})

        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json["count"], 2)
        self.assertEqual(len(json["results"]), 2)
        self.assertIn("username", json["results"][0])
        self.assertIn("status", json["results"][0])
        self.assertIn("status_text", json["results"][0])
        self.assertIn("amount", json["results"][0])
        self.assertIn("kind", json["results"][0])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # When: bill exists with consumptions and pagination
    # Then: should return paginated results with limit/offset
    def test_consumptions__with_pagination(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_bill",
            provisioning_bill=1,
            academy=1,
            provisioning_user_consumption=5,
            provisioning_consumption_kind=1,
        )
        self.client.force_authenticate(model.user)

        # Link consumptions to bill
        for consumption in model.provisioning_user_consumption:
            consumption.bills.add(model.provisioning_bill)
            consumption.save()

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1}) + "?limit=2&offset=0"

        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json["count"], 5)
        self.assertEqual(len(json["results"]), 2)
        self.assertIsNotNone(json["next"])
        self.assertIsNone(json["previous"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # When: bill exists with consumptions and pagination offset
    # Then: should return paginated results with previous/next
    def test_consumptions__with_pagination_offset(self):

        model = self.bc.database.create(
            user=1,
            profile_academy=1,
            role=1,
            capability="read_provisioning_bill",
            provisioning_bill=1,
            academy=1,
            provisioning_user_consumption=5,
            provisioning_consumption_kind=1,
        )
        self.client.force_authenticate(model.user)

        # Link consumptions to bill
        for consumption in model.provisioning_user_consumption:
            consumption.bills.add(model.provisioning_bill)
            consumption.save()

        self.headers(academy=1)

        url = reverse_lazy("provisioning:academy_bill_consumptions", kwargs={"bill_id": 1}) + "?limit=2&offset=2"

        response = self.client.get(url)

        json = response.json()
        self.assertEqual(json["count"], 5)
        self.assertEqual(len(json["results"]), 2)
        self.assertIsNotNone(json["next"])
        self.assertIsNotNone(json["previous"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

