import hashlib
from unittest.mock import MagicMock, call, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase
import breathecode.certificate.tasks as tasks
from django.utils import timezone


def remove_is_clean_for_one_item(item):
    if 'is_cleaned' in item:
        del item['is_cleaned']
    return item


def generate_update_hash(instance):
    kwargs = {
        'signed_by': instance.signed_by,
        'signed_by_role': instance.signed_by_role,
        'status': instance.status,
        'layout': instance.layout,
        'expires_at': instance.expires_at,
        'issued_at': instance.issued_at,
    }

    important_fields = ['signed_by', 'signed_by_role', 'status', 'layout', 'expires_at', 'issued_at']

    important_values = '-'.join(
        [str(kwargs.get(field) if field in kwargs else None) for field in sorted(important_fields)])

    return hashlib.sha1(important_values.encode('UTF-8')).hexdigest()


class TestAcademyEvent(LegacyAPITestCase):
    """
    🔽🔽🔽 Status ERROR
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_error(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'ERROR'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PENDING
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_pending(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PENDING'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing signed_by
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_signed_by(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by': 'GOD 🤷‍♂️',
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing signed_by_role
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_signed_by_role(
            self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by_role = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by_role': 'GOD 🤷‍♂️',
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing layout
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_layout(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model1 = self.bc.database.create(user_specialty=user_specialty)
        model2 = self.bc.database.create(layout_design=1)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model1.user_specialty))

        model1.user_specialty.layout = model2.layout_design
        model1.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'layout_id': 1,
                             'update_hash': generate_update_hash(model1.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing expires_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_expires_at(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.expires_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'expires_at': utc_now,
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url is empty, changing issued_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_is_empty__changing_issued_at(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': ''}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.issued_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [call(1), call(1)])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'issued_at': utc_now,
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'), [user_specialty_db])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing signed_by
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_signed_by(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by': 'GOD 🤷‍♂️',
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing signed_by_role
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_signed_by_role(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        model.user_specialty.signed_by_role = 'GOD 🤷‍♂️'
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'signed_by_role': 'GOD 🤷‍♂️',
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing layout
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_layout(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model1 = self.bc.database.create(user_specialty=user_specialty)
        model2 = self.bc.database.create(layout_design=1)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model1.user_specialty))

        model1.user_specialty.layout = model2.layout_design
        model1.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'layout_id': 1,
                             'update_hash': generate_update_hash(model1.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing expires_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_expires_at(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.expires_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'expires_at': utc_now,
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])

    """
    🔽🔽🔽 Status PERSISTED and preview_url set, changing issued_at
    """

    @patch('breathecode.certificate.tasks.reset_screenshot.delay', MagicMock())
    @patch('breathecode.certificate.tasks.take_screenshot.delay', MagicMock())
    def test_user_specialty_saved__status_persisted__preview_url_set__changing_issued_at(self, enable_signals):
        enable_signals()

        user_specialty = {'status': 'PERSISTED', 'preview_url': 'GOD 🤷‍♂️'}
        model = self.bc.database.create(user_specialty=user_specialty)
        user_specialty_db = remove_is_clean_for_one_item(self.bc.format.to_dict(model.user_specialty))

        utc_now = timezone.now()
        model.user_specialty.issued_at = utc_now
        model.user_specialty.save()

        self.assertEqual(tasks.reset_screenshot.delay.call_args_list, [call(1), call(1)])
        self.assertEqual(tasks.take_screenshot.delay.call_args_list, [])

        self.assertEqual(self.bc.database.list_of('certificate.UserSpecialty'),
                         [{
                             **user_specialty_db,
                             'issued_at': utc_now,
                             'update_hash': generate_update_hash(model.user_specialty),
                         }])
