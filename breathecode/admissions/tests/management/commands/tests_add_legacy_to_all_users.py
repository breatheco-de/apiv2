"""
Test /academy/cohort
"""

from mixer.backend.django import mixer

from ...mixins import AdmissionsTestCase
from ....management.commands.add_legacy_to_all_users import Command


class AcademyCohortTestSuite(AdmissionsTestCase):
    """Test /academy/cohort"""

    # When: 0 User
    # Then: does not migrate any user
    def test_0_users(self):
        """Test /academy/cohort without auth"""
        self.bc.database.create()
        command = Command()

        self.assertEqual(command.handle(), None)
        self.assertEqual(self.bc.database.list_of("auth.User"), [])

    # When: 2 User and 1 Group called Legacy
    # Then: link Legacy group to both users
    def test_2_users(self):
        """Test /academy/cohort without auth"""
        user = {"groups": []}
        model = self.bc.database.create(user=(2, user), group={"name": "Legacy"})
        command = Command()

        self.assertEqual(command.handle(), None)
        self.assertEqual(self.bc.database.list_of("auth.User"), self.bc.format.to_dict(model.user))
        self.bc.check.queryset_with_pks(model.user[0].groups.all(), [1])
        self.bc.check.queryset_with_pks(model.user[1].groups.all(), [1])
