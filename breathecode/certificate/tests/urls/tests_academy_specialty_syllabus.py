"""
POST /v1/certificate/academy/specialty/<specialty_id>/syllabus
"""

from rest_framework import status

from breathecode.certificate.models import Specialty

from ..mixins import CertificateTestCase


class AcademySpecialtySyllabusTestSuite(CertificateTestCase):
    """Link syllabus to specialty — uniqueness per academy bucket."""

    def test_link_syllabus_rejects_second_specialty_same_academy_bucket(self):
        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            academy=True,
            syllabus=True,
        )
        academy = model["academy"]
        syllabus = model["syllabus"]
        if syllabus.academy_owner_id is None:
            syllabus.academy_owner = academy
            syllabus.save()

        s1 = Specialty.objects.create(slug="syllabus-bucket-s1", name="S1", academy_id=academy.id)
        s2 = Specialty.objects.create(slug="syllabus-bucket-s2", name="S2", academy_id=academy.id)

        url1 = f"/v1/certificate/academy/specialty/{s1.id}/syllabus"
        r1 = self.client.post(url1, {"syllabus_id": syllabus.id}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)

        url2 = f"/v1/certificate/academy/specialty/{s2.id}/syllabus"
        r2 = self.client.post(url2, {"syllabus_id": syllabus.id}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r2.json().get("detail"), "syllabus-specialty-already-linked")

    def test_link_same_syllabus_allowed_for_different_academy_specialties(self):
        from breathecode.admissions.models import Academy

        self.headers(academy=1)
        model = self.generate_models(
            authenticate=True,
            profile_academy=True,
            capability="crud_syllabus",
            role="potato",
            academy=True,
            syllabus=True,
        )
        academy1 = model["academy"]
        syllabus = model["syllabus"]
        if syllabus.academy_owner_id is None:
            syllabus.academy_owner = academy1
            syllabus.save()

        academy2 = Academy.objects.create(
            slug="academy-two-syllabus-link",
            name="Academy Two",
            logo_url="https://example.com/l.png",
            icon_url="/static/icons/picture.png",
            street_address="456",
            city_id=academy1.city_id,
            country_id=academy1.country_id,
        )

        self.generate_models(
            profile_academy=True,
            models={
                "user": model["user"],
                "academy": academy2,
                "capability": model["capability"],
                "role": model["role"],
            },
        )

        s1 = Specialty.objects.create(slug="cross-a1-spec", name="A1 Spec", academy_id=academy1.id)
        s2 = Specialty.objects.create(slug="cross-a2-spec", name="A2 Spec", academy_id=academy2.id)
        s1.syllabuses.add(syllabus)

        self.headers(academy=academy2.id)
        url = f"/v1/certificate/academy/specialty/{s2.id}/syllabus"
        response = self.client.post(url, {"syllabus_id": syllabus.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
