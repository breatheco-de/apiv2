"""
GET /v1/certificate/academy/specialty — queryset visibility (same filter as the view).

The HTTP list applies PostgreSQL-only ordering (.extra); this test asserts the
academy scope filter without hitting that SQL.
"""

from django.db.models import Q

from breathecode.admissions.models import Academy
from breathecode.certificate.models import Specialty
from breathecode.certificate.views import _specialty_visible_to_academy_q

from ..mixins import CertificateTestCase


class AcademySpecialtyListTestSuite(CertificateTestCase):
    def test_queryset_excludes_other_academy_specialty_even_if_syllabus_shared(self):
        model = self.generate_models(academy=True, syllabus=True)
        academy1 = model["academy"]
        syllabus = model["syllabus"]
        if syllabus.academy_owner_id is None:
            syllabus.academy_owner = academy1
            syllabus.save()

        academy2 = Academy.objects.create(
            slug="academy-two-spec-list",
            name="Academy Two",
            logo_url="https://example.com/l.png",
            icon_url="/static/icons/picture.png",
            street_address="456",
            city_id=academy1.city_id,
            country_id=academy1.country_id,
        )

        spec_global = Specialty.objects.create(slug="spec-global-list", name="Global", academy_id=None)
        spec_ours = Specialty.objects.create(slug="spec-ours-list", name="Ours", academy_id=academy1.id)
        spec_theirs = Specialty.objects.create(slug="spec-theirs-list", name="Theirs", academy_id=academy2.id)
        spec_global.syllabuses.add(syllabus)
        spec_ours.syllabuses.add(syllabus)
        spec_theirs.syllabuses.add(syllabus)

        qs = (
            Specialty.objects.filter(
                (Q(syllabuses__academy_owner=academy1.id) | Q(academy_id=academy1.id))
                & _specialty_visible_to_academy_q(academy1.id)
            )
            .exclude(status=Specialty.DELETED)
            .distinct()
        )
        ids = set(qs.values_list("id", flat=True))
        self.assertIn(spec_global.id, ids)
        self.assertIn(spec_ours.id, ids)
        self.assertNotIn(spec_theirs.id, ids)
