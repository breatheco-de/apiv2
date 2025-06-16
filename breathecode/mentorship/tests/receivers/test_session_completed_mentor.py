from unittest.mock import MagicMock, patch

from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestSessionCompletedMentorReceiver(LegacyAPITestCase):
    """
    Test the signal receiver that sends an email to mentors when a session is completed.
    """

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_completed__no_mentor(self, enable_signals):
        """Test that no email is sent when session has no mentor"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        mentorship_session = {"status": "COMPLETED", "mentor": None}
        self.bc.database.create(mentorship_session=mentorship_session, mentorship_service=1)

        self.assertEqual(send_email_message.call_args_list, [])

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_completed__mentor_without_user(self, enable_signals):
        """Test that no email is sent when mentor has no user"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        mentorship_session = {"status": "COMPLETED"}
        mentor_profile = {"user": None}
        self.bc.database.create(
            mentorship_session=mentorship_session,
            mentor_profile=mentor_profile,
            mentorship_service=1,
        )

        self.assertEqual(send_email_message.call_args_list, [])

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_not_completed(self, enable_signals):
        """Test that no email is sent when session is not completed"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        mentorship_session = {"status": "PENDING"}
        self.bc.database.create(
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            user=1,
        )

        self.assertEqual(send_email_message.call_args_list, [])

    @patch("breathecode.authenticate.models.Token.get_or_create")
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_completed__with_mentor_and_mentee(self, mock_token, enable_signals):
        """Test that email is sent when session is completed with mentor and mentee"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        # Mock token creation
        mock_token_obj = MagicMock()
        mock_token_obj.key = "test_token_key"
        mock_token.return_value = (mock_token_obj, True)

        # Create test data
        mentorship_session = {"status": "COMPLETED"}
        model = self.bc.database.create(
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            user=2,  # One user for mentor, one for mentee
        )

        # Update session to have completed status
        model.mentorship_session.status = "COMPLETED"
        model.mentorship_session.save()

        # Verify token was created for mentor
        mock_token.assert_called_once_with(model.mentor_profile.user, token_type="temporal", hours_length=24)

        # Verify email was sent
        self.assertEqual(len(send_email_message.call_args_list), 1)
        call_args = send_email_message.call_args_list[0]

        # Check template slug
        self.assertEqual(call_args[0][0], "session_completed_mentor")
        # Check recipient email
        self.assertEqual(call_args[0][1], model.mentor_profile.user.email)
        # Check academy
        self.assertEqual(call_args[1]["academy"], model.mentor_profile.academy)

        # Check email data
        email_data = call_args[0][2]
        self.assertEqual(email_data["SUBJECT"], "Please complete your mentorship session feedback")
        self.assertIn("test_token_key", email_data["LINK"])
        self.assertEqual(email_data["SESSION_ID"], model.mentorship_session.id)
        self.assertEqual(email_data["SERVICE_NAME"], model.mentorship_service.name)
        self.assertEqual(email_data["BUTTON"], "Complete Session Feedback")

    @patch("breathecode.authenticate.models.Token.get_or_create")
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_completed__with_mentor_no_mentee(self, mock_token, enable_signals):
        """Test that email is sent when session is completed even without mentee"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        # Mock token creation
        mock_token_obj = MagicMock()
        mock_token_obj.key = "test_token_key"
        mock_token.return_value = (mock_token_obj, True)

        # Create test data without mentee
        mentorship_session = {"status": "COMPLETED", "mentee": None}
        model = self.bc.database.create(
            mentorship_session=mentorship_session,
            mentor_profile=1,
            mentorship_service=1,
            user=1,
        )

        # Update session to have completed status
        model.mentorship_session.status = "COMPLETED"
        model.mentorship_session.save()

        # Verify email was sent
        self.assertEqual(len(send_email_message.call_args_list), 1)
        call_args = send_email_message.call_args_list[0]

        # Check email data
        email_data = call_args[0][2]
        self.assertEqual(email_data["MENTEE_NAME"], "a student")

    @patch("breathecode.authenticate.models.Token.get_or_create")
    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    def test_session_completed__mentee_with_names(self, mock_token, enable_signals):
        """Test that mentee name is properly formatted when available"""
        enable_signals()

        from breathecode.notify.actions import send_email_message

        # Mock token creation
        mock_token_obj = MagicMock()
        mock_token_obj.key = "test_token_key"
        mock_token.return_value = (mock_token_obj, True)

        # Create test data with mentee having names
        user_mentor = {"first_name": "John", "last_name": "Mentor", "email": "mentor@test.com"}
        user_mentee = {"first_name": "Jane", "last_name": "Student", "email": "student@test.com"}

        model = self.bc.database.create(
            user=[user_mentor, user_mentee],
            mentor_profile={"user_id": 1},
            mentorship_session={"status": "COMPLETED", "mentee_id": 2},
            mentorship_service=1,
        )

        # Update session to have completed status
        model.mentorship_session.status = "COMPLETED"
        model.mentorship_session.save()

        # Verify email was sent
        self.assertEqual(len(send_email_message.call_args_list), 1)
        call_args = send_email_message.call_args_list[0]

        # Check email data
        email_data = call_args[0][2]
        self.assertEqual(email_data["MENTEE_NAME"], "Jane Student")
        self.assertEqual(email_data["MENTOR_NAME"], "John Mentor")
