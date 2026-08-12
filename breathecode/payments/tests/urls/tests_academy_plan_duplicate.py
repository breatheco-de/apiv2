from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments.models import Plan, PlanServiceItem

from ..mixins import PaymentsTestCase


class AcademyPlanDuplicateTestSuite(PaymentsTestCase):
    def test__no_auth(self):
        url = reverse_lazy("payments:academy_plan_id_duplicate", kwargs={"plan_id": 1})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Plan.objects.count(), 0)

    def test__no_capability(self):
        model = self.bc.database.create(user=1, academy=1)
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=model.academy.id)

        url = reverse_lazy("payments:academy_plan_id_duplicate", kwargs={"plan_id": 1})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Plan.objects.count(), 0)

    def test__not_found(self):
        model = self.bc.database.create(
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=model.academy.id)

        url = reverse_lazy("payments:academy_plan_id_duplicate", kwargs={"plan_id": 1})
        response = self.client.post(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "not-found", "status_code": 404})
        self.assertEqual(Plan.objects.count(), 0)

    def test__duplicates_plan_and_related_configuration_by_slug(self):
        plan_data = {
            "slug": "professional-plan",
            "title": "Professional Plan",
            "time_of_life": None,
            "time_of_life_unit": None,
            "is_renewable": True,
            "price_per_month": 99,
            "pricing_ratio_exceptions": {"VE": 0.5},
        }
        model = self.bc.database.create(
            plan=plan_data,
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
            financing_option=1,
            academy_service=1,
            service_item=1,
        )
        original_plan = model.plan
        addon_plan = Plan.objects.create(
            slug="addon-plan",
            currency=model.currency,
            owner=model.academy,
            time_of_life=None,
            time_of_life_unit=None,
        )
        original_plan.financing_options.add(model.financing_option)
        original_plan.add_ons.add(model.academy_service)
        original_plan.plan_addons.add(addon_plan)
        PlanServiceItem.objects.create(plan=original_plan, service_item=model.service_item)

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=model.academy.id)

        url = reverse_lazy(
            "payments:academy_plan_slug_duplicate",
            kwargs={"plan_slug": original_plan.slug},
        )
        response = self.client.post(
            url,
            {"slug": "custom-professional-plan", "title": "Custom Professional Plan"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        duplicated_plan = Plan.objects.get(slug="custom-professional-plan")
        self.assertEqual(response.json()["id"], duplicated_plan.id)
        self.assertEqual(duplicated_plan.title, "Custom Professional Plan")
        self.assertEqual(duplicated_plan.owner_id, original_plan.owner_id)
        self.assertEqual(duplicated_plan.price_per_month, original_plan.price_per_month)
        self.assertEqual(duplicated_plan.pricing_ratio_exceptions, original_plan.pricing_ratio_exceptions)
        self.assertEqual(
            list(duplicated_plan.financing_options.values_list("id", flat=True)),
            [model.financing_option.id],
        )
        self.assertEqual(
            list(duplicated_plan.add_ons.values_list("id", flat=True)),
            [model.academy_service.id],
        )
        self.assertEqual(
            list(duplicated_plan.plan_addons.values_list("id", flat=True)),
            [addon_plan.id],
        )
        self.assertEqual(
            list(duplicated_plan.service_items.values_list("id", flat=True)),
            [model.service_item.id],
        )

    def test__cannot_duplicate_with_an_existing_slug(self):
        model = self.bc.database.create(
            plan={
                "slug": "professional-plan",
                "time_of_life": None,
                "time_of_life_unit": None,
                "is_renewable": True,
            },
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=model.academy.id)

        url = reverse_lazy("payments:academy_plan_id_duplicate", kwargs={"plan_id": model.plan.id})
        response = self.client.post(url, {"slug": model.plan.slug}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "slug-already-exists", "status_code": 400})
        self.assertEqual(Plan.objects.count(), 1)
