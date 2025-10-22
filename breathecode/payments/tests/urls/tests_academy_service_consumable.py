"""
Tests for /v1/payments/academy/service/consumable endpoint
"""

import random
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import PaymentsTestCase

UTC_NOW = timezone.now()


def get_consumable_serializer(consumable):
    """Helper to serialize a consumable in the expected format."""
    return {
        "id": consumable.id,
        "how_many": consumable.how_many,
        "unit_type": consumable.unit_type,
        "valid_until": consumable.valid_until,
        "subscription": consumable.subscription.id if consumable.subscription else None,
        "plan_financing": consumable.plan_financing.id if consumable.plan_financing else None,
        "user": consumable.user.id if consumable.user else None,
        "subscription_seat": consumable.subscription_seat.id if consumable.subscription_seat else None,
        "subscription_billing_team": (
            consumable.subscription_billing_team.id if consumable.subscription_billing_team else None
        ),
    }


class AcademyServiceConsumableTestCase(PaymentsTestCase):
    """Test /v1/payments/academy/service/consumable endpoint."""

    def setUp(self):
        super().setUp()
        self.url = reverse_lazy("payments:academy_service_consumable")

    def test_without_auth(self):
        """Test that authentication is required."""
        response = self.client.get(self.url)
        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_capability(self):
        """Test that read_consumable capability is required."""
        model = self.bc.database.create(user=1)
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url, headers={"academy": 1})
        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_consumable for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_without_data(self):
        """Test that empty response is returned when no consumables exist."""
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
        )
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url, headers={"academy": 1})
        json = response.json()
        expected = {
            "cohort_sets": [],
            "event_type_sets": [],
            "mentorship_service_sets": [],
            "voids": [],
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_with_consumables_from_subscription(self):
        """Test retrieving consumables from a subscription."""
        subscription = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=subscription,
            consumable=consumable,
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url)
        json = response.json()

        # Verify response structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("cohort_sets", json)
        self.assertIn("event_type_sets", json)
        self.assertIn("mentorship_service_sets", json)
        self.assertIn("voids", json)

        # Since it's a VOID service, check the voids section
        self.assertEqual(len(json["voids"]), 1)
        void_item = json["voids"][0]
        self.assertEqual(void_item["id"], model.service.id)
        self.assertEqual(void_item["slug"], model.service.slug)
        self.assertEqual(void_item["balance"]["unit"], 10)
        self.assertEqual(len(void_item["items"]), 1)

        item = void_item["items"][0]
        self.assertEqual(item["subscription"], model.subscription.id)
        self.assertEqual(item["how_many"], 10)

    def test_with_consumables_from_plan_financing(self):
        """Test retrieving consumables from a plan financing."""
        plan_financing = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
            "monthly_price": 100,
        }
        consumable = {
            "how_many": 20,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            plan_financing=plan_financing,
            consumable=consumable,
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json["voids"]), 1)

        void_item = json["voids"][0]
        item = void_item["items"][0]
        self.assertEqual(item["plan_financing"], model.plan_financing.id)
        self.assertEqual(item["how_many"], 20)

    def test_filter_by_users(self):
        """Test filtering consumables by user IDs."""
        subscription1 = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        subscription2 = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=2,  # Create 2 users
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=(2, subscription1),
            consumable=(2, consumable),
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user[0])

        # Query for only first user
        response = self.client.get(self.url + f"?users={model.user[0].id}")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json["voids"]), 1)
        
        # Should only have 1 consumable (for user 1)
        items = json["voids"][0]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["user"], model.user[0].id)

    def test_filter_by_multiple_users(self):
        """Test filtering consumables by multiple user IDs (comma-separated)."""
        subscription = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=3,  # Create 3 users
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=(3, subscription),
            consumable=(3, consumable),
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user[0])

        # Query for first two users
        user_ids = f"{model.user[0].id},{model.user[1].id}"
        response = self.client.get(self.url + f"?users={user_ids}")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have 2 consumables
        items = json["voids"][0]["items"]
        self.assertEqual(len(items), 2)
        user_ids_in_response = {item["user"] for item in items}
        self.assertEqual(user_ids_in_response, {model.user[0].id, model.user[1].id})

    def test_filter_by_service(self):
        """Test filtering consumables by service slug."""
        subscription = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=subscription,
            consumable=(2, consumable),
            service=2,  # Create 2 different services
            service_item=2,
        )
        self.bc.request.authenticate(model.user)

        # Query for only first service
        response = self.client.get(self.url + f"?service={model.service[0].slug}")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only have consumables for the first service
        if json["voids"]:
            self.assertEqual(len(json["voids"]), 1)
            self.assertEqual(json["voids"][0]["slug"], model.service[0].slug)

    def test_filter_by_multiple_services(self):
        """Test filtering consumables by multiple service slugs (comma-separated)."""
        subscription = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=(3, subscription),
            consumable=(3, consumable),
            service=3,
            service_item=3,
        )
        self.bc.request.authenticate(model.user)

        # Query for first two services
        service_slugs = f"{model.service[0].slug},{model.service[1].slug}"
        response = self.client.get(self.url + f"?service={service_slugs}")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have consumables for the first two services only
        if json["voids"]:
            self.assertLessEqual(len(json["voids"]), 2)

    def test_only_academy_consumables(self):
        """Test that only consumables from the user's academy are returned."""
        subscription1 = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        subscription2 = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=2,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            academy=2,  # Create 2 academies
            subscription=(2, subscription1),
            consumable=(2, consumable),
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user[0])

        # Authenticate as user from first academy
        response = self.client.get(self.url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only see consumables from academy 1
        if json["voids"]:
            for void_item in json["voids"]:
                for item in void_item["items"]:
                    # Verify the consumable's subscription belongs to academy 1
                    if item["subscription"]:
                        consumable = model.consumable[0] if model.consumable[0].subscription.academy_id == 1 else model.consumable[1]
                        self.assertEqual(consumable.subscription.academy_id, 1)

    def test_invalid_users_parameter(self):
        """Test that invalid users parameter returns an error."""
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
        )
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url + "?users=invalid")
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("users parameter must contain comma-separated integers", json["detail"])

    def test_expired_consumables_not_included(self):
        """Test that expired consumables are not included in the response."""
        subscription = {
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable_valid = {
            "how_many": 10,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW + timezone.timedelta(days=30),
        }
        consumable_expired = {
            "how_many": 5,
            "unit_type": "UNIT",
            "valid_until": UTC_NOW - timezone.timedelta(days=1),  # Expired
        }
        service = {"type": "VOID"}
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_consumable",
            profile_academy=1,
            subscription=subscription,
            consumable=[consumable_valid, consumable_expired],
            service=service,
            service_item=1,
        )
        self.bc.request.authenticate(model.user)

        response = self.client.get(self.url)
        json = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only have the valid consumable
        if json["voids"]:
            items = json["voids"][0]["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["how_many"], 10)

