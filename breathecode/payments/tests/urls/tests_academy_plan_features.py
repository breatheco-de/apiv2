from django.urls import reverse_lazy
from rest_framework import status

from breathecode.payments.models import PlanFeatures

from ..mixins import PaymentsTestCase


class AcademyPlanFeaturesTestSuite(PaymentsTestCase):
    """PUT/GET /academy/plan/<id|slug>/features and GET /academy/planfeatures"""

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
        self.assertEqual(json["bullets"], bullets)
        self.assertEqual(json["plans"], [{"id": model.plan.id, "slug": model.plan.slug}])
        self.assertEqual(
            self.bc.database.list_of("payments.PlanFeatures"),
            [
                {
                    "id": json["id"],
                    "bullets": bullets,
                }
            ],
        )
        model.plan.refresh_from_db()
        self.assertEqual(model.plan.features_id, json["id"])

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
        model.plan.features = model.plan_features
        model.plan.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_slug_features", kwargs={"plan_slug": model.plan.slug})
        response = self.client.put(url, data={"bullets": bullets_v2}, format="json")

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets_v2)
        self.assertEqual(json["id"], model.plan_features.id)
        self.assertEqual(len(self.bc.database.list_of("payments.PlanFeatures")), 1)

    def test__put__attach_existing_plan_features(self):
        model = self.bc.database.create(
            plan=(
                {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
                {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            ),
            plan_features={"bullets": {"en": [{"title": "Shared", "description": "Shared desc"}]}},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        plan_a, plan_b = model.plan
        plan_a.features = model.plan_features
        plan_a.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": plan_b.id})
        response = self.client.put(
            url,
            data={"plan_features_id": model.plan_features.id},
            format="json",
        )

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["id"], model.plan_features.id)
        self.assertEqual(
            {(p["id"], p["slug"]) for p in json["plans"]},
            {(plan_a.id, plan_a.slug), (plan_b.id, plan_b.slug)},
        )
        plan_b.refresh_from_db()
        self.assertEqual(plan_b.features_id, model.plan_features.id)

    def test__put__fork_creates_unique_plan_features(self):
        bullets_shared = {"en": [{"title": "Shared", "description": "Shared desc"}]}
        bullets_forked = {"en": [{"title": "Unique", "description": "Only this plan"}]}
        model = self.bc.database.create(
            plan=(
                {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
                {"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            ),
            plan_features={"bullets": bullets_shared},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        plan_a, plan_b = model.plan
        plan_a.features = model.plan_features
        plan_a.save(update_fields=["features"])
        plan_b.features = model.plan_features
        plan_b.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": plan_b.id})
        response = self.client.put(
            url,
            data={"bullets": bullets_forked, "fork": True},
            format="json",
        )

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets_forked)
        self.assertEqual(json["plans"], [{"id": plan_b.id, "slug": plan_b.slug}])
        self.assertNotEqual(json["id"], model.plan_features.id)
        self.assertEqual(PlanFeatures.objects.count(), 2)

        plan_a.refresh_from_db()
        plan_b.refresh_from_db()
        self.assertEqual(plan_a.features_id, model.plan_features.id)
        self.assertEqual(plan_b.features_id, json["id"])
        self.assertEqual(plan_a.features.bullets, bullets_shared)

    def test__put__mode_create_always_creates_new(self):
        bullets_v1 = {"en": [{"title": "Old", "description": "Old"}]}
        bullets_v2 = {"en": [{"title": "New", "description": "New"}]}
        model = self.bc.database.create(
            plan={"time_of_life": None, "time_of_life_unit": None, "is_renewable": True},
            plan_features={"bullets": bullets_v1},
            user=1,
            capability="crud_subscription",
            role=1,
            profile_academy=1,
            skip_cohort=True,
        )
        model.plan.features = model.plan_features
        model.plan.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.put(
            url,
            data={"bullets": bullets_v2, "mode": "create"},
            format="json",
        )

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets_v2)
        self.assertNotEqual(json["id"], model.plan_features.id)
        self.assertEqual(PlanFeatures.objects.count(), 2)
        model.plan.refresh_from_db()
        self.assertEqual(model.plan.features_id, json["id"])

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

    def test__get__returns_bullets_and_plans(self):
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
        model.plan.features = model.plan_features
        model.plan.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_plan_id_features", kwargs={"plan_id": model.plan.id})
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json["bullets"], bullets)
        self.assertEqual(json["plans"], [{"id": model.plan.id, "slug": model.plan.slug}])

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

    def test__get__catalog_lists_plan_features(self):
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
        model.plan.features = model.plan_features
        model.plan.save(update_fields=["features"])

        self.client.force_authenticate(model.user)
        self.bc.request.set_headers(academy=1)

        url = reverse_lazy("payments:academy_planfeatures")
        response = self.client.get(url)

        json = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["id"], model.plan_features.id)
        self.assertEqual(json[0]["bullets"], bullets)
        self.assertEqual(json[0]["plans"], [{"id": model.plan.id, "slug": model.plan.slug}])
