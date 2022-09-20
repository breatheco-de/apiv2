"""
Test /cohort/all
"""
from datetime import timedelta
import random
import re
from django.urls.base import reverse_lazy
from django.utils import timezone
from rest_framework import status
from ..mixins import AdmissionsTestCase


def get_serializer(cohort, syllabus, syllabus_version):
    return {
        'id': cohort.id,
        'slug': cohort.slug,
        'name': cohort.name,
        'never_ends': cohort.never_ends,
        'private': cohort.private,
        'kickoff_date': re.sub(r'\+00:00$', 'Z', cohort.kickoff_date.isoformat()),
        'ending_date': cohort.ending_date,
        'language': cohort.language.lower(),
        'remote_available': cohort.remote_available,
        'syllabus_version': {
            'status': syllabus_version.status,
            'name': syllabus.name,
            'slug': syllabus.slug,
            'syllabus': syllabus_version.syllabus.id,
            'version': cohort.syllabus_version.version,
            'duration_in_days': syllabus.duration_in_days,
            'duration_in_hours': syllabus.duration_in_hours,
            'github_url': syllabus.github_url,
            'logo': syllabus.logo,
            'private': syllabus.private,
            'week_hours': syllabus.week_hours,
        },
        'academy': {
            'id': cohort.academy.id,
            'slug': cohort.academy.slug,
            'name': cohort.academy.name,
            'country': {
                'code': cohort.academy.country.code,
                'name': cohort.academy.country.name,
            },
            'city': {
                'name': cohort.academy.city.name,
            },
            'logo_url': cohort.academy.logo_url,
        },
        'schedule': None,
    }


class CohortAllTestSuite(AdmissionsTestCase):
    """Test /cohort/all"""

    def test_without_auth(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    def test_without_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True)
        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.count_cohort(), 0)

    def test_with_cohort_but_without_profile_academy(self):
        """Test /cohort/all without auth"""
        url = reverse_lazy('admissions:cohort_all')
        model = self.generate_models(authenticate=True, cohort=True)

        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Sort querystring
    """

    def test__with_data__with_sort(self):
        """Test /cohort/all without auth"""
        base = self.generate_models(authenticate=True,
                                    profile_academy=True,
                                    skip_cohort=True,
                                    syllabus_version=True)

        models = [self.generate_models(cohort=True, syllabus=True, models=base) for _ in range(0, 2)]
        ordened_models = sorted(models, key=lambda x: x['cohort'].slug, reverse=True)

        url = reverse_lazy('admissions:cohort_all') + '?sort=-slug'
        response = self.client.get(url)
        json = response.json()
        expected = [
            get_serializer(model.cohort, model.syllabus, model.syllabus_version) for model in ordened_models
        ]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        } for model in models])

    def test_with_data_with_bad_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_academy(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?academy={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_bad_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location=they-killed-kenny'
        response = self.client.get(url)
        json = response.json()

        self.assertEqual(json, [])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_location(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug}'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_location_with_comma(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?location={model.academy.slug},they-killed-kenny'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_upcoming_false(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=false'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_upcoming_true_without_current_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True, cohort=True, profile_academy=True)

        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_with_get_upcoming_true_with_current_data(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {'kickoff_date': timezone.now() + timedelta(days=365 * 2000)}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True,
                                     cohort_kwargs=cohort_kwargs)
        base_url = reverse_lazy('admissions:cohort_all')
        url = f'{base_url}?upcoming=true'
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = [get_serializer(model.cohort, model.syllabus, model.syllabus_version)]

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data_but_is_private(self):
        """Test /cohort/all without auth"""
        cohort_kwargs = {'private': True}
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus=True,
                                     cohort_kwargs=cohort_kwargs)

        url = reverse_lazy('admissions:cohort_all')
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Sort querystring
    """

    def test_with_data__cohort_with_stage_deleted(self):
        """Test /cohort/all without auth"""
        cohort = {'stage': 'DELETED'}
        model = self.generate_models(authenticate=True,
                                     cohort=cohort,
                                     profile_academy=True,
                                     syllabus_version=True)

        url = reverse_lazy('admissions:cohort_all') + '?stage=asdasdasd'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    """
    🔽🔽🔽 Sort querystring
    """

    def test_with_data__querystring_in_stage__not_found(self):
        """Test /cohort/all without auth"""
        model = self.generate_models(authenticate=True,
                                     cohort=True,
                                     profile_academy=True,
                                     syllabus_version=True)

        url = reverse_lazy('admissions:cohort_all') + '?stage=asdasdasd'
        response = self.client.get(url)
        json = response.json()
        expected = []

        self.assertEqual(json, expected)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [{
            **self.model_to_dict(model, 'cohort')
        }])

    def test_with_data__querystring_in_stage__found(self):
        """Test /cohort/all without auth"""
        statuses = ['INACTIVE', 'PREWORK', 'STARTED', 'FINAL_PROJECT', 'ENDED', 'DELETED']
        cases = [(x, x, random.choice([y for y in statuses if x != y]))
                 for x in statuses] + [(x, x.lower(), random.choice([y for y in statuses if x != y]))
                                       for x in statuses]

        model = self.generate_models(authenticate=True, cohort=3, profile_academy=True, syllabus_version=True)

        for current, query, bad_status in cases:
            model.cohort[0].stage = current
            model.cohort[0].save()

            model.cohort[1].stage = current
            model.cohort[1].save()

            model.cohort[2].stage = bad_status
            model.cohort[2].save()

            url = reverse_lazy('admissions:cohort_all') + f'?stage={query}'
            response = self.client.get(url)
            json = response.json()
            expected = sorted([
                get_serializer(model.cohort[0], model.syllabus, model.syllabus_version),
                get_serializer(model.cohort[1], model.syllabus, model.syllabus_version),
            ],
                              key=lambda x: self.bc.datetime.from_iso_string(x['kickoff_date']),
                              reverse=True)

            self.assertEqual(json, expected)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(self.bc.database.list_of('admissions.Cohort'), [
                {
                    **self.bc.format.to_dict(model.cohort[0]),
                    'stage': current,
                },
                {
                    **self.bc.format.to_dict(model.cohort[1]),
                    'stage': current,
                },
                {
                    **self.bc.format.to_dict(model.cohort[2]),
                    'stage': bad_status,
                },
            ])
