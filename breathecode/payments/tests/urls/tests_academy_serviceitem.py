"""
Tests for /academy/serviceitem endpoint
"""

from breathecode.payments.tests.urls.tests_service import PaymentsTestCase


class AcademyServiceItemTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 Auth
    """

    def test_no_auth(self):
        """Test that accessing without authentication returns 401"""
        url = "/v1/payments/academy/serviceitem"
        response = self.client.post(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    def test_no_capability(self):
        """Test that accessing without crud_service capability returns 403"""
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        response = self.client.post(url, headers={"academy": 1})

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: crud_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    """
    🔽🔽🔽 POST - Missing service
    """

    def test_missing_service(self):
        """Test that posting without service field returns 400"""
        model = self.bc.database.create(user=1, role=1, capability="crud_service", profile_academy=1)

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"how_many": 10}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        json = response.json()
        expected = {"detail": "service-required", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    """
    🔽🔽🔽 POST - Service not found
    """

    def test_service_not_found(self):
        """Test that posting with non-existent service returns 404"""
        model = self.bc.database.create(user=1, role=1, capability="crud_service", profile_academy=1)

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"service": 999, "how_many": 10}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        json = response.json()
        expected = {"detail": "service-not-found", "status_code": 404}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    """
    🔽🔽🔽 POST - Success with minimal data
    """

    def test_create_service_item__minimal(self):
        """Test creating a service item with minimal required fields"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_service", profile_academy=1, service={"slug": "test-service"}
        )

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"service": model.service.id, "how_many": 10}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        json = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                {
                    "how_many": 10,
                    "id": 1,
                    "is_renewable": False,
                    "is_team_allowed": False,
                    "renew_at": 1,
                    "renew_at_unit": "MONTH",
                    "service_id": model.service.id,
                    "sort_priority": 1,
                    "unit_type": "UNIT",
                }
            ],
        )

        # Check response contains expected fields
        self.assertEqual(json["how_many"], 10)
        self.assertEqual(json["service"]["slug"], "test-service")
        self.assertEqual(json["unit_type"], "UNIT")

    """
    🔽🔽🔽 POST - Success with all fields
    """

    def test_create_service_item__all_fields(self):
        """Test creating a service item with all fields"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_service", profile_academy=1, service={"slug": "test-service"}
        )

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {
            "service": model.service.id,
            "how_many": -1,  # unlimited
            "unit_type": "UNIT",
            "sort_priority": 5,
            "is_renewable": True,
            "is_team_allowed": True,
            "renew_at": 3,
            "renew_at_unit": "WEEK",
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        json = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.bc.database.list_of("payments.ServiceItem"),
            [
                {
                    "how_many": -1,
                    "id": 1,
                    "is_renewable": True,
                    "is_team_allowed": True,
                    "renew_at": 3,
                    "renew_at_unit": "WEEK",
                    "service_id": model.service.id,
                    "sort_priority": 5,
                    "unit_type": "UNIT",
                }
            ],
        )

        # Check response contains expected fields
        self.assertEqual(json["how_many"], -1)
        self.assertEqual(json["unit_type"], "UNIT")
        self.assertEqual(json["is_team_allowed"], True)

    """
    🔽🔽🔽 POST - Validation: how_many = 0 should fail
    """

    def test_create_service_item__invalid_how_many_zero(self):
        """Test that how_many=0 is rejected"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_service", profile_academy=1, service={"slug": "test-service"}
        )

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"service": model.service.id, "how_many": 0}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    """
    🔽🔽🔽 POST - Validation: how_many < -1 should fail
    """

    def test_create_service_item__invalid_how_many_negative(self):
        """Test that how_many < -1 is rejected"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_service", profile_academy=1, service={"slug": "test-service"}
        )

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"service": model.service.id, "how_many": -2}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.bc.database.list_of("payments.ServiceItem"), [])

    """
    🔽🔽🔽 POST - SEAT type auto-sets is_team_allowed
    """

    def test_create_service_item__seat_type_auto_team_allowed(self):
        """Test that SEAT type services automatically set is_team_allowed=True"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_service", profile_academy=1, service={"slug": "seat-service", "type": "SEAT"}
        )

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        data = {"service": model.service.id, "how_many": 5, "is_team_allowed": False}
        response = self.client.post(url, data, format="json", headers={"academy": 1})

        json = response.json()

        self.assertEqual(response.status_code, 201)
        # Even though we passed False, SEAT type should force it to True
        self.assertEqual(json["is_team_allowed"], True)

    """
    🔽🔽🔽 GET - Auth and permissions
    """

    def test_get__no_auth(self):
        """Test that GET without authentication returns 401"""
        url = "/v1/payments/academy/serviceitem"
        response = self.client.get(url)

        json = response.json()
        expected = {"detail": "Authentication credentials were not provided.", "status_code": 401}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 401)

    def test_get__no_capability(self):
        """Test that GET without read_service capability returns 403"""
        model = self.bc.database.create(user=1)

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        expected = {
            "detail": "You (user: 1) don't have this capability: read_service for academy 1",
            "status_code": 403,
        }

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, 403)

    """
    🔽🔽🔽 GET - List all service items
    """

    def test_get__empty_list(self):
        """Test GET returns empty list when no service items exist"""
        model = self.bc.database.create(user=1, role=1, capability="read_service", profile_academy=1)

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem"
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json, [])

