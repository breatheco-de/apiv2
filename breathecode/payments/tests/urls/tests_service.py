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

    def test_like_filter_by_slug(self):
        """Test filtering services by slug using like parameter"""
        model = self.bc.database.create(service=3, academy=1)

        model.service[0].slug = "ai-conversation-message"
        model.service[0].title = "AI Chat Messages"
        model.service[0].private = False
        model.service[0].owner = model.academy
        model.service[0].save()

        model.service[1].slug = "code-review-service"
        model.service[1].title = "Code Review Service"
        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        model.service[2].slug = "mentorship-sessions"
        model.service[2].title = "Mentorship Sessions"
        model.service[2].private = False
        model.service[2].owner = model.academy
        model.service[2].save()

        url = "/v1/payments/service?like=message"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["slug"], "ai-conversation-message")

    def test_like_filter_by_title(self):
        """Test filtering services by title using like parameter"""
        model = self.bc.database.create(service=2, academy=1)

        model.service[0].slug = "service-a"
        model.service[0].title = "Premium Code Reviews"
        model.service[0].private = False
        model.service[0].owner = model.academy
        model.service[0].save()

        model.service[1].slug = "service-b"
        model.service[1].title = "Basic Mentorship"
        model.service[1].private = False
        model.service[1].owner = model.academy
        model.service[1].save()

        url = "/v1/payments/service?like=code"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["title"], "Premium Code Reviews")

    def test_like_filter_case_insensitive(self):
        """Test that like filter is case-insensitive"""
        model = self.bc.database.create(service=1, academy=1)

        model.service.slug = "ai-conversation"
        model.service.title = "AI Conversation"
        model.service.private = False
        model.service.owner = model.academy
        model.service.save()

        # Test uppercase
        url = "/v1/payments/service?like=CONVERSATION"
        response = self.client.get(url)
        self.assertEqual(len(response.json()), 1)

        # Test lowercase
        url = "/v1/payments/service?like=conversation"
        response = self.client.get(url)
        self.assertEqual(len(response.json()), 1)

    def test_filter_by_academy_owner(self):
        """Test filtering services by academy owner"""
        academy1 = self.bc.database.create(academy=1, skip_objects=["service"]).academy
        academy2 = self.bc.database.create(academy=1, skip_objects=["service"]).academy

        model = self.bc.database.create(service=3)

        # Service owned by academy 1
        model.service[0].slug = "service-academy-1"
        model.service[0].private = False
        model.service[0].owner = academy1
        model.service[0].save()

        # Service owned by academy 2
        model.service[1].slug = "service-academy-2"
        model.service[1].private = False
        model.service[1].owner = academy2
        model.service[1].save()

        # Global service (no owner)
        model.service[2].slug = "service-global"
        model.service[2].private = False
        model.service[2].owner = None
        model.service[2].save()

        # Filter by academy 1 - should return academy 1's services + global
        url = f"/v1/payments/service?academy={academy1.id}"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        slugs = [s["slug"] for s in json]
        self.assertIn("service-academy-1", slugs)
        self.assertIn("service-global", slugs)
        self.assertNotIn("service-academy-2", slugs)

    def test_filter_by_academy_returns_global_services(self):
        """Test that filtering by academy includes global services"""
        academy1 = self.bc.database.create(academy=1, skip_objects=["service"]).academy
        model = self.bc.database.create(service=2)

        # Academy service
        model.service[0].slug = "academy-service"
        model.service[0].private = False
        model.service[0].owner = academy1
        model.service[0].save()

        # Global service
        model.service[1].slug = "global-service"
        model.service[1].private = False
        model.service[1].owner = None
        model.service[1].save()

        url = f"/v1/payments/service?academy={academy1.id}"
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        slugs = [s["slug"] for s in json]
        self.assertIn("academy-service", slugs)
        self.assertIn("global-service", slugs)


class AcademyServiceLikeFilterTestSuite(PaymentsTestCase):
    """Test suite for AcademyService 'like' search filter"""

    def test_like_filter_by_service_slug(self):
        """Test filtering academy services by service slug"""
        from breathecode.payments.models import AcademyService, Service

        model = self.bc.database.create(user=1, role=1, capability="read_academyservice", profile_academy=1, currency=1)

        # Create services manually
        service1 = Service.objects.create(slug="ai-conversation-message", title="AI Chat Messages")
        service2 = Service.objects.create(slug="code-review-service", title="Code Review Service")
        service3 = Service.objects.create(slug="mentorship-sessions", title="Mentorship Sessions")

        # Create academy services
        AcademyService.objects.create(
            academy=model.academy, service=service1, currency=model.currency, price_per_unit=0.01
        )
        AcademyService.objects.create(
            academy=model.academy, service=service2, currency=model.currency, price_per_unit=0.02
        )
        AcademyService.objects.create(
            academy=model.academy, service=service3, currency=model.currency, price_per_unit=0.03
        )

        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/academyservice?like=message"
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["service"]["slug"], "ai-conversation-message")

    def test_like_filter_by_service_title(self):
        """Test filtering academy services by service title"""
        from breathecode.payments.models import AcademyService, Service

        model = self.bc.database.create(user=1, role=1, capability="read_academyservice", profile_academy=1, currency=1)

        # Create services manually
        service1 = Service.objects.create(slug="service-a", title="Premium Code Reviews")
        service2 = Service.objects.create(slug="service-b", title="Basic Mentorship")

        # Create academy services
        AcademyService.objects.create(
            academy=model.academy, service=service1, currency=model.currency, price_per_unit=0.01
        )
        AcademyService.objects.create(
            academy=model.academy, service=service2, currency=model.currency, price_per_unit=0.02
        )

        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/academyservice?like=code"
        response = self.client.get(url, headers={"academy": 1})

        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["service"]["title"], "Premium Code Reviews")
