"""
Tests for /v1/payments/service endpoints
"""

from breathecode.payments.tests.mixins import PaymentsTestCase


class ServiceViewTestSuite(PaymentsTestCase):
    """Test suite for public Service endpoint"""

    def test_get_services__no_auth__excludes_private(self):
        """Test GET without auth excludes private services"""
        model = self.bc.database.create(service=2, academy=1)

        # Set one as private, one as public
        model.service[0].private = True
        model.service[0].owner = model.academy
        model.service[0].save()
        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        url = "/v1/payments/service"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["slug"], model.service[1].slug)
        self.assertEqual(json[0]["private"], False)

    def test_get_services__with_capability__includes_private(self):
        """Test GET with read_service capability includes private services"""
        model = self.bc.database.create(user=1, role=1, capability="read_service", profile_academy=1, service=2)

        # Set one as private, one as public
        model.service[0].private = True
        model.service[0].owner = model.academy
        model.service[0].save()
        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        self.client.force_authenticate(model.user)
        url = "/v1/payments/service?academy=1"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        # Both private and public services are returned
        slugs = [s["slug"] for s in json]
        self.assertIn(model.service[0].slug, slugs)
        self.assertIn(model.service[1].slug, slugs)

    def test_get_services__authenticated_no_capability__excludes_private(self):
        """Test GET authenticated but without capability excludes private services"""
        model = self.bc.database.create(user=1, service=2, academy=1)

        # Set one as private, one as public
        model.service[0].private = True
        model.service[0].owner = model.academy
        model.service[0].save()
        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        self.client.force_authenticate(model.user)
        url = "/v1/payments/service"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["slug"], model.service[1].slug)
        self.assertEqual(json[0]["private"], False)

    def test_get_service_by_slug__no_auth__private_returns_404(self):
        """Test GET specific private service without auth returns 404"""
        model = self.bc.database.create(service=1, academy=1)
        model.service.private = True
        model.service.owner = model.academy
        model.service.save()

        url = f"/v1/payments/service/{model.service.slug}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_service_by_slug__no_auth__public_returns_200(self):
        """Test GET specific public service without auth returns 200"""
        model = self.bc.database.create(service=1, academy=1)
        model.service.private = False
        model.service.owner = model.academy
        model.service.save()

        url = f"/v1/payments/service/{model.service.slug}"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json["slug"], model.service.slug)
        self.assertEqual(json["private"], False)

    def test_get_service_by_slug__with_capability__private_returns_200(self):
        """Test GET specific private service with capability returns 200"""
        model = self.bc.database.create(user=1, role=1, capability="read_service", profile_academy=1, service=1)
        model.service.private = True
        model.service.owner = model.academy
        model.service.save()

        self.client.force_authenticate(model.user)
        url = f"/v1/payments/service/{model.service.slug}?academy=1"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json["slug"], model.service.slug)
        self.assertEqual(json["private"], True)

    def test_get_services__all_private__no_auth__returns_empty(self):
        """Test GET when all services are private returns empty list"""
        model = self.bc.database.create(service=3, academy=1)

        # Set all as private
        for service in model.service:
            service.private = True
            service.owner = model.academy
            service.save()

        url = "/v1/payments/service"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json, [])

    def test_filter_by_group(self):
        """Test filtering services by permission group"""
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Student")

        model = self.bc.database.create(service=2, academy=1)

        model.service[0].private = False
        model.service[0].owner = model.academy
        model.service[0].groups.add(group)
        model.service[0].save()

        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        url = "/v1/payments/service?group=Student"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["slug"], model.service[0].slug)

