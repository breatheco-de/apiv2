import sys

from unittest.mock import MagicMock, call, patch
from ...mixins import EventTestCase
from ....management.commands.sync_eventbrite import Command
import breathecode.events.actions as actions


def write_mock():

    def write(self, *args):
        pass

    return MagicMock(side_effect=write)


def sync_org_events_mock():

    def sync_org_events(org):
        pass

    return MagicMock(side_effect=sync_org_events)


class SyncEventbriteTestSuite(EventTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Without pass entity argument
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    def test_sync_eventbrite__without_entity(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        command = Command()
        command.handle()

        self.assertEqual(sys.stdout.write.call_args_list, [])
        self.assertEqual(sys.stderr.write.call_args_list, [call("Entity argument not provided\n")])
        self.assertEqual(actions.sync_org_events.call_args_list, [])

    """
    🔽🔽🔽 Passing a bad entity
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    def test_sync_eventbrite__bad_entity(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        # model = self.generate_models(organization=True)
        command = Command()
        entity = "they_killed_kenny"
        command.handle(entity=entity)

        self.assertEqual(sys.stdout.write.call_args_list, [])
        self.assertEqual(sys.stderr.write.call_args_list, [call(f"Sync method for `{entity}` no Found!\n")])
        self.assertEqual(actions.sync_org_events.call_args_list, [])

    """
    🔽🔽🔽 With zero organizations
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    def test_sync_eventbrite__without_organization(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        # model = self.generate_models(organization=True)
        command = Command()
        entity = "events"

        command.handle(entity=entity)

        self.assertEqual(sys.stdout.write.call_args_list, [call("Enqueued 0 of 0 for sync events\n")])
        self.assertEqual(sys.stderr.write.call_args_list, [])
        self.assertEqual(actions.sync_org_events.call_args_list, [])

    """
    🔽🔽🔽 With one organization without eventbrite credentials without name
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    @patch("builtins.print", MagicMock())
    def test_sync_eventbrite__with_organization__without_name(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        model = self.generate_models(organization=True)
        command = Command()
        entity = "events"

        command.handle(entity=entity)

        self.assertEqual(sys.stdout.write.call_args_list, [call("Enqueued 0 of 1 for sync events\n")])
        self.assertEqual(
            sys.stderr.write.call_args_list, [call(f"Organization Nameless is missing evenbrite key or ID\n")]
        )
        self.assertEqual(actions.sync_org_events.call_args_list, [])

    """
    🔽🔽🔽 With one organization without eventbrite credentials with name
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    @patch("builtins.print", MagicMock())
    def test_sync_eventbrite__with_organization__with_name(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        organization_kwargs = {"name": "They killed kenny"}
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)
        command = Command()
        entity = "events"

        command.handle(entity=entity)

        self.assertEqual(sys.stdout.write.call_args_list, [call("Enqueued 0 of 1 for sync events\n")])
        self.assertEqual(
            sys.stderr.write.call_args_list, [call(f"Organization They killed kenny is missing evenbrite key or ID\n")]
        )
        self.assertEqual(actions.sync_org_events.call_args_list, [])

    """
    🔽🔽🔽 With one organization
    """

    @patch.object(sys.stdout, "write", write_mock())
    @patch.object(sys.stderr, "write", write_mock())
    @patch.object(actions, "sync_org_events", sync_org_events_mock())
    @patch("builtins.print", MagicMock())
    def test_sync_eventbrite__with_organization(self):
        """Test /answer without auth"""
        import breathecode.events.actions as actions
        import sys

        organization_kwargs = {
            "name": "They killed kenny",
            "eventbrite_key": "they-killed-kenny",
            "eventbrite_id": 10131911,  # don't forget 🦾
        }
        model = self.generate_models(organization=True, organization_kwargs=organization_kwargs)
        command = Command()
        entity = "events"

        command.handle(entity=entity)

        self.assertEqual(sys.stdout.write.call_args_list, [call("Enqueued 1 of 1 for sync events\n")])
        # self.assertEqual(len(sys.stderr.write.call_args_list), 1) # the test environment is not consistent
        self.assertEqual(actions.sync_org_events.call_args_list, [call(model.organization)])
