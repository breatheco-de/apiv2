"""
Test /academy
"""

from unittest.mock import MagicMock, call, patch
from logging import Logger

from breathecode.admissions.tasks import build_profile_academy
from ..mixins import AdmissionsTestCase


def profile_academy_item(user, academy, data={}):
    return {
        "academy_id": academy.id,
        "address": None,
        "email": user.email,
        "first_name": user.first_name,
        "id": 0,
        "last_name": user.last_name,
        "phone": "",
        "role_id": "",
        "status": "INVITED",
        "user_id": user.id,
        **data,
    }


class AcademyActivateTestSuite(AdmissionsTestCase):
    """Test /academy/activate"""

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_user_not_found(self):
        build_profile_academy.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
            ],
        )

        self.bc.check.calls(
            Logger.error.call_args_list,
            [
                call("User with id 1 not found", exc_info=True),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_academy_not_found(self):
        self.bc.database.create(user=1)

        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

        build_profile_academy.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
            ],
        )

        self.bc.check.calls(
            Logger.error.call_args_list,
            [
                call("Academy with id 1 not found", exc_info=True),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_role_not_found(self):
        self.bc.database.create(user=1, academy=1)

        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

        build_profile_academy.delay(1, 1)

        self.assertEqual(self.bc.database.list_of("authenticate.ProfileAcademy"), [])
        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
            ],
        )

        self.bc.check.calls(
            Logger.error.call_args_list,
            [
                call("Role with slug None not found", exc_info=True),
            ],
        )

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_role_student(self):
        model = self.bc.database.create(user=1, academy=1, role="student")

        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

        build_profile_academy.delay(1, 1)

        self.assertEqual(
            self.bc.database.list_of("authenticate.ProfileAcademy"),
            [
                profile_academy_item(
                    model.user,
                    model.academy,
                    data={
                        "id": 1,
                        "status": "ACTIVE",
                        "role_id": "student",
                    },
                ),
            ],
        )

        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
                call("ProfileAcademy added"),
            ],
        )

        self.bc.check.calls(Logger.error.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_random_role(self):
        model = self.bc.database.create(user=1, academy=1, role=1)

        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

        build_profile_academy.delay(1, 1, model.role.slug)

        self.assertEqual(
            self.bc.database.list_of("authenticate.ProfileAcademy"),
            [
                profile_academy_item(
                    model.user,
                    model.academy,
                    data={
                        "id": 1,
                        "status": "ACTIVE",
                        "role_id": model.role.slug,
                    },
                ),
            ],
        )

        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
                call("ProfileAcademy added"),
            ],
        )

        self.bc.check.calls(Logger.error.call_args_list, [])

    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    def test_profile_academy_exists(self):
        model = self.bc.database.create(user=1, academy=1, role=1, profile_academy=1)

        Logger.info.call_args_list = []
        Logger.error.call_args_list = []

        build_profile_academy.delay(1, 1, model.role.slug)

        self.assertEqual(
            self.bc.database.list_of("authenticate.ProfileAcademy"),
            [
                {
                    **self.bc.format.to_dict(model.profile_academy),
                    "id": 1,
                    "status": "ACTIVE",
                    "role_id": model.role.slug,
                },
            ],
        )

        self.bc.check.calls(
            Logger.info.call_args_list,
            [
                call("Starting build_profile_academy for cohort 1 and user 1"),
                call("ProfileAcademy mark as active"),
            ],
        )

        self.bc.check.calls(Logger.error.call_args_list, [])
