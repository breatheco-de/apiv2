"""
Test /answer
"""
import os
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch

from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.services.google_cloud import Datastore

from ..mixins import AssignmentsTestCase
from ...tasks import teacher_task_notification


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Without env
    """
    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value=None))
    def test_teacher_task_notification__without_env(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(os.getenv.call_args_list, [call('TEACHER_URL')])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list,
                         [call('TEACHER_URL is not set as environment variable')])

    """
    🔽🔽🔽 Without Task
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value='https://hardcoded.url'))
    def test_teacher_task_notification__without_tasks(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        # os.environ['TEACHER_URL'] = 'https://hardcoded.url'

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(os.getenv.call_args_list, [call('TEACHER_URL')])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list, [call('Task not found')])

    """
    🔽🔽🔽 With Task
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value='https://hardcoded.url'))
    def test_teacher_task_notification__with_task(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        model = self.bc.database.create(task=1)

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(os.getenv.call_args_list, [call('TEACHER_URL')])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list, [call('Can\'t determine the student cohort')])

    """
    🔽🔽🔽 With Task and Cohort
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value='https://hardcoded.url'))
    def test_teacher_task_notification__with_task__with_cohort(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        model = self.bc.database.create(task=1, cohort=1)

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(send_email_message.call_args_list, [
            call(
                'diagnostic', model.user.email, {
                    'subject':
                    f'{model.user.first_name} {model.user.last_name} send their task',
                    'details':
                    (f'{model.user.first_name} {model.user.last_name} send their task "{model.task.title}", '
                     'you can review the task at '
                     f'https://hardcoded.url/cohort/{model.cohort.slug}/assignments')
                })
        ])
        self.assertEqual(
            os.getenv.call_args_list,
            [
                call('ENV', ''),  # this is coming from Academy.save
                call('TEACHER_URL'),
            ])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list, [])

    """
    🔽🔽🔽 With Task and Cohort in spanish
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value='https://hardcoded.url'))
    def test_teacher_task_notification__with_task__with_cohort__lang_es(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        cohort = {'language': 'es'}
        model = self.bc.database.create(task=1, cohort=cohort)

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(send_email_message.call_args_list, [
            call(
                'diagnostic', model.user.email, {
                    'subject':
                    f'{model.user.first_name} {model.user.last_name} envió su tarea',
                    'details':
                    (f'{model.user.first_name} {model.user.last_name} envió su tarea "{model.task.title}", '
                     'puedes revisarla en '
                     f'https://hardcoded.url/cohort/{model.cohort.slug}/assignments')
                })
        ])
        self.assertEqual(
            os.getenv.call_args_list,
            [
                call('ENV', ''),  # this is coming from Academy.save
                call('TEACHER_URL'),
            ])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list, [])

    """
    🔽🔽🔽 With Task and Cohort, url ends with /
    """

    @patch('breathecode.notify.actions.send_email_message', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('os.getenv', MagicMock(return_value='https://hardcoded.url/'))
    def test_teacher_task_notification__with_task__with_cohort__ends_with_slash(self):
        import os
        from logging import Logger
        from breathecode.notify.actions import send_email_message

        model = self.bc.database.create(task=1, cohort=1)

        teacher_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(send_email_message.call_args_list, [
            call(
                'diagnostic', model.user.email, {
                    'subject':
                    f'{model.user.first_name} {model.user.last_name} send their task',
                    'details':
                    (f'{model.user.first_name} {model.user.last_name} send their task "{model.task.title}", '
                     'you can review the task at '
                     f'https://hardcoded.url/cohort/{model.cohort.slug}/assignments')
                })
        ])
        self.assertEqual(
            os.getenv.call_args_list,
            [
                call('ENV', ''),  # this is coming from Academy.save
                call('TEACHER_URL'),
            ])
        self.assertEqual(Logger.debug.call_args_list, [call('Starting teacher_task_notification')])
        self.assertEqual(Logger.error.call_args_list, [])
