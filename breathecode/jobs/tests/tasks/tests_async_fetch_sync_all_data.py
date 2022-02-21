"""
Test /answer
"""

from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, call, patch
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

from ...tasks import async_run_spider, async_fetch_sync_all_data

JOBS = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/1',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile)',
    'Company_name': 'Repite Employer',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.url.com/2',
    '_type': 'dict'
}]

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class AsyncFetchSyncAllDataTaskTestCase(JobsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Without Task
    """
    @patch('breathecode.jobs.tasks.async_fetch_sync_all_data', MagicMock())
    @patch('logging.Logger.debug', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    def test_async_async_fetch_sync_all_data__without_tasks(self):
        from logging import Logger
        from breathecode.jobs.actions import save_data
        model = self.generate_models(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)
        # result = save_data(model.spider, JOBS)
        # spider = self.bc.database.list_of('jobs.Spider')
        print('id: ', model['spider'].id)
        async_fetch_sync_all_data.delay(model['spider'].id)
        print(Logger.debug.call_args_list)

        print(Logger.error.call_args_list)

        # try:
        #     async_run_spider.delay({'spi_id': 1})

        #     print(Logger.debug.call_args_list)
        #     print(Logger.error.call_args_list)
        #     assert False
        # except Exception as e:
        #     # self.assertEqual(str(e), 'missing-spider')
        #     print(Logger.debug.call_args_list)
        #     print(Logger.error.call_args_list)

        # self.assertEqual(Logger.error.call_args_list, [
        #         call('First you must specify a spider (fetch_data_to_json)'),
        #         call('Status 400 - without-spider')
        #     ])
        # try:
        #     run_spider(None)
        #     assert False
        # except Exception as e:
        #     self.assertEqual(str(e), 'missing-spider')

        # student_task_notification.delay(1)

        # self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        # self.assertEqual(send_email_message.call_args_list, [])
        # self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
        # self.assertEqual(Logger.error.call_args_list, [call('Task not found')])

    """
    🔽🔽🔽 With Task
    """

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     model = self.bc.database.create(task=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [])
    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [call('Can\'t determine the student cohort')])

    # """
    # 🔽🔽🔽 With Task and Cohort revision_status PENDING
    # """

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__pending__with_task__with_cohort(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'PENDING'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as pending'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__pending__with_cohort__url_ends_with_slash(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'PENDING'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as pending'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__pending__with_cohort__lang_es(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'PENDING'}
    #     cohort = {'language': 'es'}
    #     model = self.bc.database.create(task=task, cohort=cohort)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Tu tarea "{model.task.title}" ha sido revisada',
    #                 'details': 'Tu tarea se ha marcado como pendiente'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # """
    # 🔽🔽🔽 With Task and Cohort revision_status APPROVED
    # """

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__approved__with_task__with_cohort(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'APPROVED'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as approved'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__approved__with_cohort__url_ends_with_slash(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'APPROVED'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as approved'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__approved__with_cohort__lang_es(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'APPROVED'}
    #     cohort = {'language': 'es'}
    #     model = self.bc.database.create(task=task, cohort=cohort)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Tu tarea "{model.task.title}" ha sido revisada',
    #                 'details': 'Tu tarea se ha marcado como aprobada'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # """
    # 🔽🔽🔽 With Task and Cohort revision_status REJECTED
    # """

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__rejected__with_task__with_cohort(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'REJECTED'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as rejected'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__rejected__with_cohort__url_ends_with_slash(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'REJECTED'}
    #     model = self.bc.database.create(task=task, cohort=1)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Your task "{model.task.title}" has been reviewed',
    #                 'details': 'Your task has been marked as rejected'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])

    # @patch('breathecode.notify.actions.send_email_message', MagicMock())
    # @patch('logging.Logger.debug', MagicMock())
    # @patch('logging.Logger.error', MagicMock())
    # def test_student_task_notification__with_task__rejected__with_cohort__lang_es(self):
    #     from logging import Logger
    #     from breathecode.notify.actions import send_email_message

    #     task = {'revision_status': 'REJECTED'}
    #     cohort = {'language': 'es'}
    #     model = self.bc.database.create(task=task, cohort=cohort)

    #     student_task_notification.delay(1)

    #     self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
    #     self.assertEqual(send_email_message.call_args_list, [
    #         call(
    #             'diagnostic', model.user.email, {
    #                 'subject': f'Tu tarea "{model.task.title}" ha sido revisada',
    #                 'details': 'Tu tarea se ha marcado como rechazada'
    #             })
    #     ])

    #     self.assertEqual(Logger.debug.call_args_list, [call('Starting student_task_notification')])
    #     self.assertEqual(Logger.error.call_args_list, [])
