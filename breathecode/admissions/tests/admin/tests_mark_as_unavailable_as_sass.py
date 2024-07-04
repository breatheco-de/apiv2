"""
Test replicate_in_all
"""

from unittest.mock import MagicMock, call, patch
from breathecode.admissions.admin import mark_as_unavailable_as_saas
from django.http.request import HttpRequest
from ..mixins import AdmissionsTestCase


class CohortUserTestSuite(AdmissionsTestCase):
    """
    🔽🔽🔽 With zero Academy
    """

    def test__with_zero_academies(self):
        request = HttpRequest()
        Academy = self.bc.database.get_model("admissions.Academy")
        queryset = Academy.objects.all()

        mark_as_unavailable_as_saas(None, request, queryset)

        self.assertEqual(self.bc.database.list_of("admissions.Academy"), [])

    """
    🔽🔽🔽 With two Academy
    """

    def test__with_two_academies__available_as_saas_is_initially_false(self):
        academy = {"available_as_saas": False}
        model = self.bc.database.create(academy=(2, academy))

        request = HttpRequest()
        Academy = self.bc.database.get_model("admissions.Academy")
        queryset = Academy.objects.all()

        mark_as_unavailable_as_saas(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                {
                    **self.bc.format.to_dict(model.academy[0]),
                    "available_as_saas": False,
                },
                {
                    **self.bc.format.to_dict(model.academy[1]),
                    "available_as_saas": False,
                },
            ],
        )

    def test__with_two_academies__available_as_saas_is_initially_true(self):
        academy = {"available_as_saas": True}
        model = self.bc.database.create(academy=(2, academy))

        request = HttpRequest()
        Academy = self.bc.database.get_model("admissions.Academy")
        queryset = Academy.objects.all()

        mark_as_unavailable_as_saas(None, request, queryset)

        self.assertEqual(
            self.bc.database.list_of("admissions.Academy"),
            [
                {
                    **self.bc.format.to_dict(model.academy[0]),
                    "available_as_saas": False,
                },
                {
                    **self.bc.format.to_dict(model.academy[1]),
                    "available_as_saas": False,
                },
            ],
        )
