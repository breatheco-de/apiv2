from random import choice
from unittest.mock import MagicMock, call, patch
from breathecode.authenticate.admin import accept_selected_users_from_waiting_list
from ..mixins.new_auth_test_case import AuthTestCase
from ... import tasks


class ModelProfileAcademyTestSuite(AuthTestCase):
    """
    🔽🔽🔽 With zero UserInvite
    """

    @patch("breathecode.authenticate.tasks.async_accept_user_from_waiting_list.delay", MagicMock())
    def test_with_zero_user_invite(self):
        UserInvite = self.bc.database.get_model("authenticate.UserInvite")
        queryset = UserInvite.objects.filter()

        result = accept_selected_users_from_waiting_list(None, None, queryset)

        self.assertEqual(result, None)
        self.assertEqual(tasks.async_accept_user_from_waiting_list.delay.call_args_list, [])

    """
    🔽🔽🔽 With two UserInvite
    """

    @patch("breathecode.authenticate.tasks.async_accept_user_from_waiting_list.delay", MagicMock())
    def test_with_two_user_invites(self):
        self.bc.database.create(user_invite=2)

        UserInvite = self.bc.database.get_model("authenticate.UserInvite")
        queryset = UserInvite.objects.filter()

        result = accept_selected_users_from_waiting_list(None, None, queryset)

        self.assertEqual(result, None)
        self.assertEqual(tasks.async_accept_user_from_waiting_list.delay.call_args_list, [call(1), call(2)])

    """
    🔽🔽🔽 With four UserInvite, selecting just two items
    """

    @patch("breathecode.authenticate.tasks.async_accept_user_from_waiting_list.delay", MagicMock())
    def test_with_four_user_invites__selecting_just_two_items(self):
        options = {1, 2, 3, 4}
        self.bc.database.create(user_invite=4)

        ...
        #
        ids = []
        for _ in range(0, 2):
            selected = choice(list(options))
            options.discard(selected)
            ids.append(selected)

        ids.sort()

        UserInvite = self.bc.database.get_model("authenticate.UserInvite")
        queryset = UserInvite.objects.filter(id__in=ids)

        result = accept_selected_users_from_waiting_list(None, None, queryset)

        self.assertEqual(result, None)
        self.assertEqual(
            tasks.async_accept_user_from_waiting_list.delay.call_args_list,
            [
                call(ids[0]),
                call(ids[1]),
            ],
        )

    """
    🔽🔽🔽 With three UserInvite, passing all the valid statuses
    """

    @patch("breathecode.authenticate.tasks.async_accept_user_from_waiting_list.delay", MagicMock())
    def test_with_three_user_invites__passing_all_the_valid_statuses(self):
        user_invites = [{"process_status": x} for x in ["PENDING", "DONE", "ERROR"]]
        self.bc.database.create(user_invite=user_invites)

        UserInvite = self.bc.database.get_model("authenticate.UserInvite")
        queryset = UserInvite.objects.filter()

        result = accept_selected_users_from_waiting_list(None, None, queryset)

        self.assertEqual(result, None)
        self.assertEqual(tasks.async_accept_user_from_waiting_list.delay.call_args_list, [call(1), call(3)])
