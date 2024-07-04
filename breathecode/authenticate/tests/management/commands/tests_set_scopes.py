"""
Test /academy/cohort
"""

import random
from unittest.mock import MagicMock, call, patch

from django.core.management.base import OutputWrapper
from django.utils import timezone

from ....management.commands.set_scopes import APPS, SCOPES, Command
from ...mixins.new_auth_test_case import AuthTestCase

UTC_NOW = timezone.now()


class AcademyCohortTestSuite(AuthTestCase):

    def test__apps_format(self):
        for app in APPS:
            self.assertRegex(app["slug"], r"^[a-z:_]+$")
            self.assertRegex(app["name"], r"^[a-zA-Z ]+$")
            self.assertTrue(app["require_an_agreement"] in [True, False])

            for scope in app["required_scopes"]:
                self.assertRegex(scope, r"^[a-z:_]+$")

            for scope in app["optional_scopes"]:
                self.assertRegex(scope, r"^[a-z:-]+$")

    def test__scopes_format(self):
        for scope in SCOPES:
            self.assertRegex(scope["slug"], r"^[a-z:-]+$")
            self.assertRegex(scope["name"], r"^[a-zA-Z ]+$")
            self.assertTrue("description" in scope)

    # When: No apps
    # Then: Shouldn't made any app
    def test_no_apps(self):
        SCOPES = [
            {
                "name": self.bc.fake.name(),
                "slug": self.bc.fake.slug()[:15].replace("-", "_"),
                "description": self.bc.fake.text()[:255],
            }
            for _ in range(4)
        ]

        APPS = [
            {
                "name": self.bc.fake.name(),
                "slug": self.bc.fake.slug()[:15].replace("-", "_"),
                "require_an_agreement": bool(random.randint(0, 1)),
                "required_scopes": [SCOPES[0]["slug"], SCOPES[1]["slug"]],
                "optional_scopes": [SCOPES[2]["slug"], SCOPES[3]["slug"]],
            },
        ]

        with patch("breathecode.authenticate.management.commands.set_scopes.APPS", APPS):
            with patch("breathecode.authenticate.management.commands.set_scopes.SCOPES", SCOPES):
                command = Command()
                result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("linked_services.Scope"),
            [
                {
                    **SCOPES[0],
                    "id": 1,
                },
                {
                    **SCOPES[1],
                    "id": 2,
                },
                {
                    **SCOPES[2],
                    "id": 3,
                },
                {
                    **SCOPES[3],
                    "id": 4,
                },
            ],
        )
        self.assertEqual(self.bc.database.list_of("linked_services.App"), [])

    # When: 1 app
    # Then: Must updated it
    @patch("django.utils.timezone.now", MagicMock(return_value=UTC_NOW))
    def test_1_app(self):
        SCOPES = [
            {
                "name": self.bc.fake.name(),
                "slug": self.bc.fake.slug()[:15].replace("-", "_"),
                "description": self.bc.fake.text()[:255],
            }
            for _ in range(4)
        ]

        APPS = [
            {
                "name": self.bc.fake.name(),
                "slug": self.bc.fake.slug()[:15].replace("-", "_"),
                "require_an_agreement": bool(random.randint(0, 1)),
                "required_scopes": [SCOPES[0]["slug"], SCOPES[1]["slug"]],
                "optional_scopes": [SCOPES[2]["slug"], SCOPES[3]["slug"]],
            },
        ]

        app = {"slug": APPS[0]["slug"]}
        model = self.bc.database.create(app=app)

        with patch("breathecode.authenticate.management.commands.set_scopes.APPS", APPS):
            with patch("breathecode.authenticate.management.commands.set_scopes.SCOPES", SCOPES):
                command = Command()
                result = command.handle()

        self.assertEqual(result, None)
        self.assertEqual(
            self.bc.database.list_of("linked_services.Scope"),
            [
                {
                    **SCOPES[0],
                    "id": 1,
                },
                {
                    **SCOPES[1],
                    "id": 2,
                },
                {
                    **SCOPES[2],
                    "id": 3,
                },
                {
                    **SCOPES[3],
                    "id": 4,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("linked_services.App"),
            [
                {
                    **self.bc.format.to_dict(model.app),
                    "name": APPS[0]["name"],
                    "require_an_agreement": APPS[0]["require_an_agreement"],
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("linked_services.AppRequiredScope"),
            [
                {
                    "agreed_at": UTC_NOW,
                    "app_id": 1,
                    "id": 1,
                    "scope_id": 1,
                },
                {
                    "agreed_at": UTC_NOW,
                    "app_id": 1,
                    "id": 2,
                    "scope_id": 2,
                },
            ],
        )
        self.assertEqual(
            self.bc.database.list_of("linked_services.AppOptionalScope"),
            [
                {
                    "agreed_at": UTC_NOW,
                    "app_id": 1,
                    "id": 1,
                    "scope_id": 3,
                },
                {
                    "agreed_at": UTC_NOW,
                    "app_id": 1,
                    "id": 2,
                    "scope_id": 4,
                },
            ],
        )
