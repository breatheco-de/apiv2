from breathecode.tests.mocks.eventbrite.constants.events import EVENTBRITE_EVENTS
from ..mixins import EventTestCase
from breathecode.events.actions import create_or_update_organizer


class SyncOrgVenuesTestSuite(EventTestCase):
    """
    🔽🔽🔽 Without academy
    """

    def test_create_or_update_organizer__without_academy(self):
        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)

        with self.assertRaises(Exception) as cm:
            create_or_update_organizer(EVENTBRITE_EVENTS["events"][0], model["organization"], force_update=False)

        self.assertEqual(str(cm.exception), "First you must specify to which academy this organization belongs")

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_organizer_dict(), [])

    """
    🔽🔽🔽 With academy
    """

    def test_create_or_update_organizer__with_academy(self):
        organization_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(academy=True, organization=True, organization_kwargs=organization_kwargs)

        create_or_update_organizer(
            EVENTBRITE_EVENTS["events"][0]["organizer"], model["organization"], force_update=False
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        organizer = EVENTBRITE_EVENTS["events"][0]["organizer"]
        kwargs = {
            "id": 1,
            "name": organizer["name"],
            "description": organizer["description"]["text"],
            "eventbrite_id": organizer["id"],
            "organization_id": 1,
            "academy_id": None,
        }
        self.assertEqual(self.all_organizer_dict(), [kwargs])

    """
    🔽🔽🔽 With academy and organizer
    """

    def test_create_or_update_organizer__with_organizer(self):
        organization_kwargs = {"eventbrite_id": "1"}
        organizer_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(
            academy=True,
            organizer=True,
            organization=True,
            organizer_kwargs=organizer_kwargs,
            organization_kwargs=organization_kwargs,
        )

        create_or_update_organizer(
            EVENTBRITE_EVENTS["events"][0]["organizer"], model["organization"], force_update=False
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])
        self.assertEqual(self.all_organizer_dict(), [self.model_to_dict(model, "organizer")])

    """
    🔽🔽🔽 With academy and organizer with force update
    """

    def test_create_or_update_organizer__with_organizer__with_force_update(self):
        organization_kwargs = {"eventbrite_id": "1"}
        organizer_kwargs = {"eventbrite_id": "1"}
        model = self.generate_models(
            academy=True,
            organizer=True,
            organization=True,
            organizer_kwargs=organizer_kwargs,
            organization_kwargs=organization_kwargs,
        )

        create_or_update_organizer(
            EVENTBRITE_EVENTS["events"][0]["organizer"], model["organization"], force_update=True
        )

        self.assertEqual(self.all_organization_dict(), [self.model_to_dict(model, "organization")])

        organizer = EVENTBRITE_EVENTS["events"][0]["organizer"]
        self.assertEqual(
            self.all_organizer_dict(),
            [
                {
                    **self.model_to_dict(model, "organizer"),
                    "name": organizer["name"],
                    "description": organizer["description"]["text"],
                }
            ],
        )
