"""
Test /cohort/all
"""

import random
import re
from datetime import datetime, timedelta

from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status

from ..mixins import AdmissionsTestCase


def get_serializer(cohort, syllabus, syllabus_version, data={}):
    return {
        "id": cohort.id,
        "distance": None,
        "slug": cohort.slug,
        "name": cohort.name,
        "never_ends": cohort.never_ends,
        "private": cohort.private,
        "kickoff_date": (
            re.sub(r"\+00:00$", "Z", cohort.kickoff_date.isoformat()) if cohort.kickoff_date else cohort.kickoff_date
        ),
        "ending_date": cohort.ending_date,
        "language": cohort.language.lower(),
        "remote_available": cohort.remote_available,
        "syllabus_version": {
            "name": syllabus.name,
            "status": syllabus_version.status,
            "slug": syllabus.slug,
            "syllabus": syllabus_version.syllabus.id,
            "version": cohort.syllabus_version.version,
            "duration_in_days": syllabus.duration_in_days,
            "duration_in_hours": syllabus.duration_in_hours,
            "github_url": syllabus.github_url,
            "logo": syllabus.logo,
            "private": syllabus.private,
            "week_hours": syllabus.week_hours,
        },
        "academy": {
            "id": cohort.academy.id,
            "slug": cohort.academy.slug,
            "name": cohort.academy.name,
            "country": {
                "code": cohort.academy.country.code,
                "name": cohort.academy.country.name,
            },
            "city": {
                "name": cohort.academy.city.name,
            },
            "logo_url": cohort.academy.logo_url,
            "is_hidden_on_prework": cohort.academy.is_hidden_on_prework,
        },
        "schedule": None,
        "timeslots": [],
        "timezone": None,
        **data,
    }


class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""

    def test_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy("admissions:cohort_all")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    def test_without_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy("admissions:cohort_all")
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    """
    🔽🔽🔽 Sort querystring
    """

    def test__with_data__with_sort(self):
        """Test /cohort/all without auth"""
        base = self.generate_models(authenticate=True, profile_academy=True, skip_cohort=True, syllabus_version=True)

        models = [self.generate_models(cohort=True, syllabus=True, models=base) for _ in range(0, 2)]
        ordened_models = sorted(models, key=lambda x: x["cohort"].slug, reverse=True)

        url = reverse_lazy("admissions:cohort_all") + "?sort=-slug"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version) for model in ordened_models]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")} for model in models]
        )

    def test_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?academy=they-killed-kenny"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?academy={model.academy.slug}"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?location=they-killed-kenny"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?location={model.academy.slug}"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_location_with_comma(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?location={model.academy.slug},they-killed-kenny"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?upcoming=false"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_upcoming_true_without_current_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?upcoming=true"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_with_get_upcoming_true_with_current_data(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {"kickoff_date": timezone.now() + timedelta(days=365 * 2000)}
        model = self.generate_models(
            authenticate=True, cohort=True, profile_academy=True, syllabus_version=True, cohort_kwargs=cohort_kwargs
        )
        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?upcoming=true"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all")
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data_but_is_private(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {"private": True}
        model = self.generate_models(
            authenticate=True, cohort=True, profile_academy=True, syllabus=True, cohort_kwargs=cohort_kwargs
        )

        url = reverse_lazy("admissions:cohort_all")
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    """
    🔽🔽🔽 Sort querystring
    """

    def test_with_data__cohort_with_stage_deleted(self):
        """Test /cohort/all without auth"""
        cohort = {"stage": "DELETED"}
        model = self.generate_models(authenticate=True, cohort=cohort, profile_academy=True, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all") + "?stage=asdasdasd"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    """
    🔽🔽🔽 Sort querystring
    """

    def test_with_data__querystring_in_stage__not_found(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all") + "?coordinates=a"
        response = self.client.get(url)
        json = response.json()
        expected = {"detail": "bad-coordinates", "status_code": 400}

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__querystring_in_stage__found(self):
        """Test /cohort/all without auth"""
        statuses = ["INACTIVE", "PREWORK", "STARTED", "FINAL_PROJECT", "ENDED", "DELETED"]
        cases = [(x, x, random.choice([y for y in statuses if x != y])) for x in statuses] + [
            (x, x.lower(), random.choice([y for y in statuses if x != y])) for x in statuses
        ]

        cohorts = [{"kickoff_date": datetime.today().isoformat()} for n in range(0, 3)]
        model = self.generate_models(authenticate=True, cohort=cohorts, profile_academy=True, syllabus_version=True)

        for current, query, bad_status in cases:
            model.cohort[0].stage = current
            model.cohort[0].save()

            model.cohort[1].stage = current
            model.cohort[1].save()

            model.cohort[2].stage = bad_status
            model.cohort[2].save()

            url = reverse_lazy("admissions:cohort_all") + f"?stage={query}"
            response = self.client.get(url)
            json = response.json()
            expected = sorted(
                [
                    get_serializer(model.cohort[0], model.syllabus, model.syllabus_version),
                    get_serializer(model.cohort[1], model.syllabus, model.syllabus_version),
                ],
                key=lambda x: self.bc.datetime.from_iso_string(x["kickoff_date"]),
                reverse=True,
            )

            for j in json:
                del j["kickoff_date"]
            for i in expected:
                del i["kickoff_date"]
            list_of_cohorts = self.bc.database.list_of("admissions.Cohort")
            cohorts_dict = self.bc.format.to_dict(model.cohort)
            for j in list_of_cohorts:
                del j["kickoff_date"]
            for i in cohorts_dict:
                del i["kickoff_date"]
            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                list_of_cohorts,
                cohorts_dict,
            )

    def test_with_data__distance_is_none(self):
        """Test /cohort/all without auth"""
        cases = [
            ("", None, None),
            ("", 1, None),
            ("", None, 1),
            ("", 1, 1),
            ("1,1", None, None),
            ("1,1", 1, None),
            ("1,1", None, 1),
        ]
        model = self.generate_models(cohort=True, syllabus_version=True)

        for query, latitude, longitude in cases:
            model.academy.latitude = latitude
            model.academy.longitude = longitude
            model.academy.save()

            url = reverse_lazy("admissions:cohort_all") + "?coordinates=" + query
            response = self.client.get(url)
            json = response.json()
            expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version, data={"distance": None})]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__bad_coordinates(self):
        """Test /cohort/all without auth"""
        cases = [
            ("1", None, None),
            ("1,", None, None),
            ("1,a", None, None),
            ("a,1", None, None),
        ]
        model = self.generate_models(cohort=True, syllabus_version=True)

        for query, latitude, longitude in cases:
            model.academy.latitude = latitude
            model.academy.longitude = longitude
            model.academy.save()

            url = reverse_lazy("admissions:cohort_all") + "?coordinates=" + query
            response = self.client.get(url)
            json = response.json()
            expected = {"detail": "bad-coordinates", "status_code": 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__bad_coordinates__invalid_values(self):
        """Test /cohort/all without auth"""
        cases = [
            ("91,180", None, None, "bad-latitude"),
            ("-91,-180", None, None, "bad-latitude"),
            ("91,-180", None, None, "bad-latitude"),
            ("-91,180", None, None, "bad-latitude"),
            ("90,181", None, None, "bad-longitude"),
            ("-90,-181", None, None, "bad-longitude"),
            ("90,-181", None, None, "bad-longitude"),
            ("-90,181", None, None, "bad-longitude"),
        ]
        model = self.generate_models(cohort=True, syllabus_version=True)

        for query, latitude, longitude, error in cases:
            model.academy.latitude = latitude
            model.academy.longitude = longitude
            model.academy.save()

            url = reverse_lazy("admissions:cohort_all") + "?coordinates=" + query
            response = self.client.get(url)
            json = response.json()
            expected = {"detail": error, "status_code": 400}

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__good_coordinates__check_same_distance_with_different_symbols(self):
        """Test /cohort/all without auth"""
        cases = [
            ("90,180", 80, 180),
            ("-90,-180", -80, -180),
            ("90,-180", 80, -180),
            ("-90,180", -80, 180),
            ("90,180", 80, 180),
            ("-90,-180", -80, -180),
            ("90,-180", 80, -180),
            ("-90,180", -80, 180),
        ]
        model = self.generate_models(cohort=True, syllabus_version=True)

        for query, latitude, longitude in cases:
            model.academy.latitude = latitude
            model.academy.longitude = longitude
            model.academy.save()

            url = reverse_lazy("admissions:cohort_all") + "?coordinates=" + query
            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(
                    model.cohort, model.syllabus, model.syllabus_version, data={"distance": 1111.9492664455875}
                )
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__good_coordinates__generating_correct_distance(self):
        """Test /cohort/all without auth"""
        cases = [
            ("76,90", 76, 130, 1055.5073456754758),
            ("-54,-133", -60, -99, 2136.8610368766904),
            ("33,-1", 90, -33, 6338.110818739848),
            ("-56,167", 43, -165, 11318.400937786448),
        ]
        model = self.generate_models(cohort=True, syllabus_version=True)

        for query, latitude, longitude, distance in cases:
            model.academy.latitude = latitude
            model.academy.longitude = longitude
            model.academy.save()

            url = reverse_lazy("admissions:cohort_all") + "?coordinates=" + query
            response = self.client.get(url)
            json = response.json()
            expected = [
                get_serializer(model.cohort, model.syllabus, model.syllabus_version, data={"distance": distance})
            ]

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_with_data__good_coordinates__sorting_the_distances(self):
        """Test /cohort/all without auth"""
        distance1 = 5081.175052677738
        distance2 = 11318.400937786448
        distance3 = 14915.309490907744
        distance4 = 16234.459290105573
        academies = [
            {
                "latitude": -60,
                "longitude": -99,
            },
            {
                "latitude": 76,
                "longitude": 130,
            },
            {
                "latitude": 43,
                "longitude": -165,
            },
            {
                "latitude": 90,
                "longitude": -33,
            },
        ]
        cohorts = [{"academy_id": n} for n in range(1, 5)]
        model = self.generate_models(academy=academies, cohort=cohorts, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all") + "?coordinates=-56,167"
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(model.cohort[0], model.syllabus, model.syllabus_version, data={"distance": distance1}),
            get_serializer(model.cohort[2], model.syllabus, model.syllabus_version, data={"distance": distance2}),
            get_serializer(model.cohort[1], model.syllabus, model.syllabus_version, data={"distance": distance3}),
            get_serializer(model.cohort[3], model.syllabus, model.syllabus_version, data={"distance": distance4}),
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), self.bc.format.to_dict(model.cohort))

    """
    🔽🔽🔽 saas in querystring
    """

    def test_with_data__empty_and_random_saas_in_querystring(self):
        cases = ["", self.bc.fake.slug()]
        academies = [
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
        ]
        cohorts = [{"academy_id": n, "kickoff_date": datetime.today().isoformat()} for n in range(1, 5)]
        model = self.generate_models(academy=academies, cohort=cohorts, syllabus_version=True)

        for query in cases:
            url = reverse_lazy("admissions:cohort_all") + f"?saas={query}"
            response = self.client.get(url)
            json = response.json()
            expected = sorted(
                [
                    get_serializer(model.cohort[0], model.syllabus, model.syllabus_version, data={"distance": None}),
                    get_serializer(model.cohort[1], model.syllabus, model.syllabus_version, data={"distance": None}),
                    get_serializer(model.cohort[2], model.syllabus, model.syllabus_version, data={"distance": None}),
                    get_serializer(model.cohort[3], model.syllabus, model.syllabus_version, data={"distance": None}),
                ],
                key=lambda x: self.bc.datetime.from_iso_string(x["kickoff_date"]),
                reverse=True,
            )

            for j in json:
                del j["kickoff_date"]
            for i in expected:
                del i["kickoff_date"]
            list_of_cohorts = self.bc.database.list_of("admissions.Cohort")
            cohorts_dict = self.bc.format.to_dict(model.cohort)
            for j in list_of_cohorts:
                del j["kickoff_date"]
            for i in cohorts_dict:
                del i["kickoff_date"]
            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(list_of_cohorts, cohorts_dict)

    def test_with_data__saas_is_false(self):
        academies = [
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
        ]
        cohorts = [{"academy_id": n, "kickoff_date": datetime.today().isoformat()} for n in range(1, 5)]
        model = self.generate_models(academy=academies, cohort=cohorts, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all") + f"?saas=false"
        response = self.client.get(url)
        json = response.json()
        expected = sorted(
            [
                get_serializer(model.cohort[1], model.syllabus, model.syllabus_version, data={"distance": None}),
                get_serializer(model.cohort[3], model.syllabus, model.syllabus_version, data={"distance": None}),
            ],
            key=lambda x: self.bc.datetime.from_iso_string(x["kickoff_date"]),
            reverse=True,
        )

        for j in json:
            del j["kickoff_date"]
        for i in expected:
            del i["kickoff_date"]
        list_of_cohorts = self.bc.database.list_of("admissions.Cohort")
        cohorts_dict = self.bc.format.to_dict(model.cohort)
        for j in list_of_cohorts:
            del j["kickoff_date"]
        for i in cohorts_dict:
            del i["kickoff_date"]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_of_cohorts, cohorts_dict)

    def test_with_data__saas_is_true(self):
        academies = [
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
            {
                "available_as_saas": True,
            },
            {
                "available_as_saas": False,
            },
        ]
        cohorts = [{"academy_id": n, "kickoff_date": datetime.today()} for n in range(1, 5)]
        model = self.generate_models(academy=academies, cohort=cohorts, syllabus_version=True)

        url = reverse_lazy("admissions:cohort_all") + f"?saas=true"
        response = self.client.get(url)
        json = response.json()
        expected = sorted(
            [
                get_serializer(model.cohort[0], model.syllabus, model.syllabus_version, data={"distance": None}),
                get_serializer(model.cohort[2], model.syllabus, model.syllabus_version, data={"distance": None}),
            ],
            key=lambda x: self.bc.datetime.from_iso_string(x["kickoff_date"]),
            reverse=True,
        )

        for j in json:
            del j["kickoff_date"]
        for i in expected:
            del i["kickoff_date"]
        list_of_cohorts = self.bc.database.list_of("admissions.Cohort")
        cohorts_dict = self.bc.format.to_dict(model.cohort)
        for j in list_of_cohorts:
            del j["kickoff_date"]
        for i in cohorts_dict:
            del i["kickoff_date"]
        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_of_cohorts, cohorts_dict)

    """
    🔽🔽🔽 GET with plan=true in querystring
    """

    def test_plan_true__without_scheduler(self):
        """Test /cohort/all without auth"""
        cohort = {"available_as_saas": True}
        model = self.generate_models(authenticate=True, cohort=cohort, profile_academy=1)

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?plan=true"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_plan_true__with_scheduler(self):
        """Test /cohort/all without auth"""
        plan = {"time_of_life": None, "time_of_life_unit": None}
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}
        model = self.generate_models(
            authenticate=True,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            profile_academy=1,
            syllabus_version=1,
            currency=1,
            plan_service_item=1,
            mentorship_service=1,
            mentorship_service_set=1,
            plan=plan,
            academy=academy,
        )

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?plan=true"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    """
    🔽🔽🔽 GET with plan=false in querystring
    """

    def test_plan_false__without_scheduler(self):
        """Test /cohort/all without auth"""
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}
        model = self.generate_models(
            authenticate=True,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            profile_academy=1,
            syllabus_version=1,
            academy=academy,
        )

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?plan=false"
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_plan_false__with_scheduler(self):
        """Test /cohort/all without auth"""
        plan = {"time_of_life": None, "time_of_life_unit": None}
        cohort = {"available_as_saas": True}
        model = self.generate_models(
            authenticate=True,
            cohort=cohort,
            profile_academy=1,
            syllabus_version=1,
            currency=1,
            plan_service_item=1,
            mentorship_service=1,
            mentorship_service_set=1,
            plan=plan,
        )

        base_url = reverse_lazy("admissions:cohort_all")
        url = f"{base_url}?plan=false"
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    """
    🔽🔽🔽 GET with plan as slug in querystring
    """

    def test_plan_is_slug__without_scheduler(self):
        """Test /cohort/all without auth"""
        cohort = {"available_as_saas": True}
        model = self.generate_models(authenticate=True, cohort=cohort, profile_academy=1)
        slug = self.bc.fake.slug()

        url = reverse_lazy("admissions:cohort_all") + f"?plan={slug}"
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])

    def test_plan_is_slug__with_scheduler(self):
        """Test /cohort/all without auth"""
        slug = self.bc.fake.slug()
        plan = {"slug": slug, "time_of_life": None, "time_of_life_unit": None}
        cohort = {"available_as_saas": True}
        academy = {"available_as_saas": True}

        model = self.generate_models(
            authenticate=True,
            cohort=cohort,
            cohort_set=1,
            cohort_set_cohort=1,
            profile_academy=1,
            syllabus_version=1,
            currency=1,
            plan_service_item=1,
            mentorship_service=1,
            mentorship_service_set=1,
            plan=plan,
            academy=academy,
        )

        url = reverse_lazy("admissions:cohort_all") + f"?plan={slug}"
        response = self.client.get(url)
        json = response.json()

        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.bc.database.list_of("admissions.Cohort"), [{**self.model_to_dict(model, "cohort")}])
