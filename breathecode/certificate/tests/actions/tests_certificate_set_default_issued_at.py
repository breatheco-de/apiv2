"""
Tasks tests
"""
from unittest.mock import patch, call, MagicMock
from ...actions import certificate_set_default_issued_at
from ..mixins import CertificateTestCase
from ...models import UserSpecialty

from django.utils import timezone


class ActionCertificateSetDefaultIssuedAtTestCase(CertificateTestCase):
    def test_issued_at_null_status_error(self):

        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'ERROR',
                                         'issued_at': None
                                     })
        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'ERROR',
                'issued_at': None,
            }]))

    def test_issued_at_set_status_error(self):

        now = timezone.now()

        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'ERROR',
                                         'issued_at': now
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'ERROR',
                'issued_at': now,
            }]))

    def test_issued_at_null_status_persisted_one_item(self):

        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'PERSISTED',
                                         'issued_at': None
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': None,
            }]))

    def test_issued_at_null_status_persisted_two_items(self):

        model1 = self.generate_models(user_specialty=True,
                                      user_specialty_kwargs={
                                          'status': 'PERSISTED',
                                          'issued_at': None,
                                          'token': '123abcd'
                                      })
        model2 = self.generate_models(user_specialty=True,
                                      user_specialty_kwargs={
                                          'status': 'PERSISTED',
                                          'issued_at': None,
                                          'token': '567pqrst'
                                      })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model1, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': None,
            }, {
                **self.model_to_dict(model2, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': None,
            }]))

    def test_issued_at_null_status_persisted_one_item_with_cohort(self):

        model = self.generate_models(user_specialty=True,
                                     cohort=True,
                                     user_specialty_kwargs={
                                         'status': 'PERSISTED',
                                         'issued_at': None
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': model.cohort.ending_date,
            }]))

    def test_issued_at_null_status_persisted_two_items_with_cohort(self):

        model1 = self.generate_models(user_specialty=True,
                                      cohort=True,
                                      user_specialty_kwargs={
                                          'status': 'PERSISTED',
                                          'issued_at': None,
                                          'token': '123abcd'
                                      })
        model2 = self.generate_models(user_specialty=True,
                                      cohort=True,
                                      user_specialty_kwargs={
                                          'status': 'PERSISTED',
                                          'issued_at': None,
                                          'token': '567pqrst'
                                      })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model1, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': model1.cohort.ending_date,
            }, {
                **self.model_to_dict(model2, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': model2.cohort.ending_date,
            }]))

    def test_issued_at_set_status_persisted(self):
        now = timezone.now()
        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'PERSISTED',
                                         'issued_at': now
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'PERSISTED',
                'issued_at': now,
            }]))

    def test_issued_at_set_status_pending(self):

        now = timezone.now()
        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'PENDING',
                                         'issued_at': now
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'PENDING',
                'issued_at': now,
            }]))

    def test_issued_at_null_status_pending(self):

        model = self.generate_models(user_specialty=True,
                                     user_specialty_kwargs={
                                         'status': 'PENDING',
                                         'issued_at': None
                                     })

        query = UserSpecialty.objects.filter(status='PERSISTED', issued_at__isnull=True)

        result = certificate_set_default_issued_at()

        self.assertEqual(list(result), list(query))
        self.assertEqual(
            self.all_user_specialty_dict(),
            self.remove_is_clean([{
                **self.model_to_dict(model, 'user_specialty'),
                'status': 'PENDING',
                'issued_at': None,
            }]))
