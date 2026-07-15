from django.urls import reverse_lazy
from rest_framework import status

from ..mixins import PaymentsTestCase


class AcademyPlanFeaturesTestSuite(PaymentsTestCase):
    """PUT/GET /academy/plan/<id|slug>/features"""

    def test__put__no_auth(self):
        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": 1})
        response = self.client.put(url, data={"bullets": {"en": []}}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test__put__creates_plan_features(self):
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        bullets = {
            "en": [{"title": "AI", "description": "English description"}],
            "es": [{"title": "IA", "description": "Descripcion en espanol"}],
        }
        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.put(url, data={"bullets": bullets}, format="json")

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["plan"], model.plan.id)
        self.assertEqual(json["plan_slug"], model.plan.slug)
        self.assertEqual(json["bullets"], bullets)
        self.assertEqual(self.bc.database.list_of("payments.PlanFeatures"), [
            {
                "id": json["id"],
                "plan_id": model.plan.id,
                "bullets": bullets,
            }
        ])

    def test__put__updates_existing_plan_features_by_slug(self):
        bullets_v1 = {"en": [{"title": "Old", "description": "Old desc"}]}
        bullets_v2 = {
            "en": [{"title": "New", "description": "New desc"}],
            "es": [{"title": "Nuevo", "description": "Nueva desc"}],
        }
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            plan_features={"bullets": bullets_v1},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_slug_features", kwargs={"plan_slug": model.plan.slug})
        response = self.client.put(url, data={"bullets": bullets_v2}, format="json")

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets_v2)
        self.assertEqual(len(self.bc.database.list_of("payments.PlanFeatures")), 1)

    def test__put__invalid_bullets_format(self):
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.put(url, data={"bullets": ["not-an-object"]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["slug"], "invalid-bullets-format")

    def test__get__returns_bullets(self):
        bullets = {"en": [{"title": "AI", "description": "English description"}]}
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            plan_features={"bullets": bullets},
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets)

    def test__get__not_found_without_plan_features(self):
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            user=1,
            capability="read_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["slug"], "plan-features-not-found")
