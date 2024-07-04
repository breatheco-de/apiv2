"""
Test /answer
"""

from django.utils import timezone
from task_manager.core.exceptions import RetryTask

from breathecode.activity.actions import FillActivityMeta

from ..mixins import MediaTestCase

UTC_NOW = timezone.now()


class UserTestSuite(MediaTestCase):

    def test_id_not_found(self):
        kind = self.bc.fake.slug()

        with self.assertRaisesMessage(RetryTask, f"User 1 not found"):
            FillActivityMeta.user(kind, 1, None)

    def test_slug_not_found(self):
        kind = self.bc.fake.slug()

        model = self.bc.database.create(user=1)

        meta = FillActivityMeta.user(kind, 1, None)
        expected = {
            "email": model.user.email,
            "id": model.user.id,
            "username": model.user.username,
        }

        self.assertEqual(meta, expected)
        self.assertEqual(self.bc.database.list_of("auth.User"), [self.bc.format.to_dict(model.user)])
