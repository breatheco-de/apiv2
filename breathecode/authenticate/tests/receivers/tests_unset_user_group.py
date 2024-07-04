from unittest.mock import MagicMock, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase


def capitalize(string: str) -> str:
    return string[0].upper() + string[1:]


class TestModelProfileAcademy(LegacyAPITestCase):
    """
    🔽🔽🔽 Adding a ProfileAcademy, with bad role
    """

    @patch("django.db.models.signals.post_save.send_robust", MagicMock())
    def test_adding_a_profile_academy__with_bad_role(self, enable_signals):
        enable_signals()

        group = {"name": "Student"}
        model = self.bc.database.create(profile_academy=1, group=group)
        model.profile_academy.delete()

        self.assertEqual(self.bc.database.list_of("auth.Group"), [{"id": 1, "name": "Student"}])
        self.assertEqual(self.bc.format.table(model.user.groups.all()), [{"id": 1, "name": "Student"}])

    """
    🔽🔽🔽 Adding a ProfileAcademy, with right role, status INVITED
    """

    @patch("django.db.models.signals.post_save.send_robust", MagicMock())
    def test_adding_a_profile_academy__with_right_role__status_invited(self, enable_signals):
        enable_signals()

        cases = ["student", "teacher"]
        for case in cases:
            group_name = capitalize(case)
            group = {"name": group_name}
            model = self.bc.database.create(profile_academy=1, group=group, role=case)
            model.profile_academy.delete()

            self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])
            self.assertEqual(
                self.bc.format.table(model.user.groups.all()),
                [
                    self.bc.format.to_dict(model.group),
                ],
            )

            # teardown
            self.bc.database.delete("auth.Group")

    """
    🔽🔽🔽 Adding a ProfileAcademy, with right role, status ACTIVE
    """

    @patch("django.db.models.signals.post_save.send_robust", MagicMock())
    def test_adding_a_profile_academy__with_right_role__status_active(self, enable_signals):
        enable_signals()

        cases = ["student", "teacher"]
        for case in cases:
            group_name = capitalize(case)
            group = {"name": group_name}
            profile_academy = {"status": "ACTIVE"}
            model = self.bc.database.create(profile_academy=profile_academy, group=group, role=case)
            model.profile_academy.delete()

            self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])
            self.assertEqual(self.bc.format.table(model.user.groups.all()), [])

            # teardown
            self.bc.database.delete("auth.Group")

    """
    🔽🔽🔽 Adding two ProfileAcademy, with right role, status ACTIVE
    """

    @patch("django.db.models.signals.post_save.send_robust", MagicMock())
    def test_adding_two_profile_academy__with_right_role__status_active(self, enable_signals):
        enable_signals()

        cases = ["student", "teacher"]
        for case in cases:
            group_name = capitalize(case)
            group = {"name": group_name}
            profile_academy = {"status": "ACTIVE"}
            model = self.bc.database.create(profile_academy=(2, profile_academy), group=group, role=case)
            model.profile_academy[0].delete()

            self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])
            self.assertEqual(
                self.bc.format.table(model.user.groups.all()),
                [
                    self.bc.format.to_dict(model.group),
                ],
            )

            # teardown
            self.bc.database.delete("auth.Group")


class TestModelMentorProfile(LegacyAPITestCase):
    """
    🔽🔽🔽 Adding a ProfileAcademy
    """

    def test_adding_a_mentor_profile(self, enable_signals):
        enable_signals()

        group = {"name": "Mentor"}
        model = self.bc.database.create(mentor_profile=1, group=group)

        model.mentor_profile.delete()

        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])
        self.assertEqual(self.bc.format.table(model.user.groups.all()), [])

    """
    🔽🔽🔽 Adding two ProfileAcademy
    """

    def test_adding_two_mentor_profile(self, enable_signals):
        enable_signals()

        group = {"name": "Mentor"}
        model = self.bc.database.create(mentor_profile=2, group=group)

        model.mentor_profile[0].delete()

        self.assertEqual(self.bc.database.list_of("auth.Group"), [self.bc.format.to_dict(model.group)])
        self.assertEqual(
            self.bc.format.table(model.user.groups.all()),
            [
                self.bc.format.to_dict(model.group),
            ],
        )
