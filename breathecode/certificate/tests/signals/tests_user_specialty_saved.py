import hashlib
from unittest.mock import MagicMock, call, patch
from ..mixins import CertificateTestCase
import breathecode.certificate.signals as signals
import breathecode.certificate.tasks as tasks
from django.utils import timezone


class AcademyEventTestSuite(CertificateTestCase):
    """
    🔽🔽🔽 Status ERROR
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_error(self):
        user_specialty = {'status': 'ERROR'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PENDING
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_pending(self):
        user_specialty = {'status': 'PENDING'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing signed_by
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_signed_by(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by': 'GOD 🤷‍♂️',
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing signed_by_role
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_signed_by_role(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by_role = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by_role': 'GOD 🤷‍♂️',
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing layout
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_layout(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model1 = self.bc.database.create(user_specialty=user_specialty)
        model2 = self.bc.database.create(layout_design=1)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model1.user_specialty))

        model1.user_specialty.layout = model2.layout_design
        model1.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'layout_id': 1,
                             'update_hash': self.generate_update_hash(model1.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing expires_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_expires_at(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.expires_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'expires_at': utc_now,
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing issued_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_issued_at(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.issued_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'issued_at': utc_now,
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing signed_by
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_signed_by(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by': 'GOD 🤷‍♂️',
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing signed_by_role
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_signed_by_role(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by_role = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by_role': 'GOD 🤷‍♂️',
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing layout
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_layout(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model1 = self.bc.database.create(user_specialty=user_specialty)
        model2 = self.bc.database.create(layout_design=1)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model1.user_specialty))

        model1.user_specialty.layout = model2.layout_design
        model1.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'layout_id': 1,
                             'update_hash': self.generate_update_hash(model1.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing expires_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_expires_at(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.expires_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'expires_at': utc_now,
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing issued_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_issued_at(self):
        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = self.remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.issued_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'issued_at': utc_now,
                             'update_hash': self.generate_update_hash(model.user_specialty),
                         }])
