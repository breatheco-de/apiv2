"""
Tasks tests
"""
from unittest.mock import patch, call, MagicMock
from breathecode.certificate import signals
from ...actions import certificate_set_default_issued_at
from ..mixins import CertificateTestCase
from ...models import UserSpecialty
from django.utils import timezone


class ActionCertificateSetDefaultIssuedAtTestCase(CertificateTestCase):
    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_null_status_error(self):
        # the issues_at should remain None because the certificate generation gave an error.

        model = self.generate_models(user_specialty=True,
                                     cohort=False,
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_set_status_error(self):
        # the issues_at should remain the same and not be modified because the certificate gave an error.

        now = timezone.now()

        model = self.generate_models(user_specialty=True,
                                     cohort=False,
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_null_status_persisted_one_item(self):
        # The issued_at should remain None because the user_specialty does not have cohort specified,
        # and it is impossible to determine cohort ending_at

        model = self.generate_models(user_specialty=True,
                                     cohort=False,
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_null_status_persisted_two_items(self):
        # both certificates should have issued_at None because both cohorts are null

        model1 = self.generate_models(user_specialty=True,
                                      cohort=False,
                                      user_specialty_kwargs={
                                          'status': 'PERSISTED',
                                          'issued_at': None,
                                          'token': '123abcd'
                                      })
        model2 = self.generate_models(user_specialty=True,
                                      cohort=False,
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model1.user_specialty, sender=model1.user_specialty.__class__),
            call(instance=model2.user_specialty, sender=model2.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model.user_specialty, sender=model.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
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

        self.assertEqual(signals.user_specialty_saved.send.call_args_list, [
            call(instance=model1.user_specialty, sender=model1.user_specialty.__class__),
            call(instance=model2.user_specialty, sender=model2.user_specialty.__class__),
        ])

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_set_status_persisted(self):
        # issuet_at should remain the same because there was already a value so the default should no be applied.
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

        self.assertEqual(str(signals.user_specialty_saved.send.call_args_list),
                         str([
                             call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                         ]))

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_set_status_pending(self):
        # issuet_at should remain the same because there was already a value so the default should no be applied.

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

        self.assertEqual(str(signals.user_specialty_saved.send.call_args_list),
                         str([
                             call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                         ]))

    @patch('breathecode.certificate.signals.user_specialty_saved.send', MagicMock())
    def test_issued_at_null_status_pending(self):
        # issuet_at should remain the same because status=Pending

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

        self.assertEqual(str(signals.user_specialty_saved.send.call_args_list),
                         str([
                             call(instance=model.user_specialty, sender=model.user_specialty.__class__),
                         ]))
