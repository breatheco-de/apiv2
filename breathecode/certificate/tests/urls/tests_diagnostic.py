"""
GET /v1/certificate/diagnostic — student graduation/certificate diagnostics.
"""

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from breathecode.admissions.models import Academy, Cohort, CohortUser

from ..mixins import CertificateTestCase


class CertificateDiagnosticTestSuite(CertificateTestCase):
    def test_diagnostic__without_auth(self):
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(url, {"kind": "graduation", "cohort_user_id": 1})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_diagnostic__without_capability(self):
        self.headers(academy=1)
        self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="read_asset",
            role="potato",
        )
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(url, {"kind": "graduation", "cohort_user_id": 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_diagnostic__missing_kind(self):
        self.headers(academy=1)
        self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
        )
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(url, {"cohort_user_id": 1})
        json = response.json()
        self.assertEqual(json.get("slug"), "invalid-diagnostic-kind")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_diagnostic__graduation_by_cohort_user_id(self):
        self.headers(academy=1)
        cohort_user_kwargs = {"role": "STUDENT"}
        self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
            cohort=True,
            user=True,
            cohort_user=True,
            syllabus_version=True,
            cohort_user_kwargs=cohort_user_kwargs,
        )
        cu = CohortUser.objects.filter(role="STUDENT").first()
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(
            url,
            {"kind": "graduation", "cohort_user_id": cu.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["kind"], "graduation")
        self.assertEqual(data["academy_id"], 1)
        self.assertIn("result", data)
        self.assertEqual(data["result"]["cohort_user_id"], cu.id)

    def test_diagnostic__certificate_by_cohort_user_id(self):
        self.headers(academy=1)
        cohort_user_kwargs = {"role": "STUDENT"}
        self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
            cohort=True,
            user=True,
            cohort_user=True,
            syllabus_version=True,
            specialty=True,
            cohort_user_kwargs=cohort_user_kwargs,
        )
        cu = CohortUser.objects.filter(role="STUDENT").first()
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(
            url,
            {"kind": "certificate", "cohort_user_id": cu.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["kind"], "certificate")
        self.assertIn("checks", data["result"])

    def test_diagnostic__cohort_user_wrong_academy(self):
        """CohortUser belongs to another academy → 404."""
        self.headers(academy=1)
        base = self.generate_models(academy=True, user=True)
        academy2 = Academy.objects.create(
            slug="other-academy-diag",
            name="Other",
            logo_url="https://example.com/l.png",
            icon_url="/static/icons/picture.png",
            street_address="456",
            city_id=base["academy"].city_id,
            country_id=base["academy"].country_id,
        )
        cohort = Cohort.objects.create(
            slug="c-other-diag-wrong-academy",
            name="Other Cohort",
            academy=academy2,
            kickoff_date=timezone.now(),
        )
        user = base["user"]
        cu = CohortUser.objects.create(user=user, cohort=cohort, role="STUDENT")

        self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
            models=base,
        )
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(
            url,
            {"kind": "graduation", "cohort_user_id": cu.id},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json().get("slug"), "cohort-user-not-found")

    def test_diagnostic__ambiguous_multi_cohort(self):
        self.headers(academy=1)
        cohort_user_kwargs = {"role": "STUDENT"}
        base = self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
            cohort=True,
            user=True,
            cohort_user=True,
            syllabus_version=True,
            cohort_user_kwargs=cohort_user_kwargs,
        )
        user = base["user"]
        c2 = Cohort.objects.create(
            slug="cohort-two-diag-ambiguous",
            name="Cohort Two",
            academy_id=base["academy"].id,
            kickoff_date=timezone.now(),
        )
        CohortUser.objects.create(user=user, cohort=c2, role="STUDENT")

        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(
            url,
            {"kind": "graduation", "user_id": user.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get("slug"), "ambiguous-cohort-user")

    def test_diagnostic__scope_cohort_limit(self):
        self.headers(academy=1)
        cohort_user_kwargs = {"role": "STUDENT"}
        base = self.generate_models(
            authenticate=True,
            capability="read_certificate",
            profile_academy=True,
            role="potato",
            cohort=True,
            user=True,
            cohort_user=True,
            syllabus_version=True,
            cohort_user_kwargs=cohort_user_kwargs,
        )
        cohort_id = base["cohort"].id
        url = reverse_lazy("certificate:diagnostic")
        response = self.client.get(
            url,
            {
                "kind": "certificate",
                "scope": "cohort",
                "cohort_id": cohort_id,
                "limit": "2",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
