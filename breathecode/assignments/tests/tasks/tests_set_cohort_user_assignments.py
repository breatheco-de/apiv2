"""
Test /answer
"""

import random
from unittest.mock import MagicMock, call, patch

from breathecode.assignments import signals
from logging import Logger

from ..mixins import AssignmentsTestCase
from ...tasks import set_cohort_user_assignments


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""
    """
    🔽🔽🔽 Without Task
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__without_tasks(self):
        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(Logger.info.call_args_list, [call('Executing set_cohort_user_assignments')])
        self.assertEqual(Logger.error.call_args_list, [call('Task not found')])

    """
    🔽🔽🔽 One Task
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task(self):
        model = self.bc.database.create(task=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [])
        self.assertEqual(Logger.info.call_args_list, [call('Executing set_cohort_user_assignments')])
        self.assertEqual(Logger.error.call_args_list, [call('CohortUser not found')])

    """
    🔽🔽🔽 One Task
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_pending(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'PENDING',
            'task_type': task_type,
        }
        model = self.bc.database.create(task=task, cohort_user=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [],
                    'pending_assignments': [
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_done(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'DONE',
            'task_type': task_type,
        }
        model = self.bc.database.create(task=task, cohort_user=1)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                    'pending_assignments': [],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])

    """
    🔽🔽🔽 One Task with log
    """

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_pending__with_log__already_exists(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'PENDING',
            'task_type': task_type,
        }
        cohort_user = {
            'history_log': {
                'delivered_assignments': [],
                'pending_assignments': [
                    {
                        'id': 1,
                        'type': task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [],
                    'pending_assignments': [
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_pending__with_log__from_different_items(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'PENDING',
            'task_type': task_type,
        }
        cohort_user = {
            'history_log': {
                'delivered_assignments': [
                    {
                        'id': 3,
                        'type': task_type,
                    },
                ],
                'pending_assignments': [
                    {
                        'id': 2,
                        'type': task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [
                        {
                            'id': 3,
                            'type': task_type,
                        },
                    ],
                    'pending_assignments': [
                        {
                            'id': 2,
                            'type': task_type,
                        },
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_done__with_log__already_exists(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'DONE',
            'task_type': task_type,
        }
        cohort_user = {
            'history_log': {
                'delivered_assignments': [
                    {
                        'id': 1,
                        'type': task_type,
                    },
                ],
                'pending_assignments': [],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                    'pending_assignments': [],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])

    @patch('logging.Logger.info', MagicMock())
    @patch('logging.Logger.error', MagicMock())
    @patch('breathecode.assignments.signals.assignment_created.send', MagicMock())
    @patch('breathecode.assignments.signals.assignment_status_updated.send', MagicMock())
    @patch('breathecode.activity.tasks.get_attendancy_log.delay', MagicMock())
    def test__with_one_task__task_is_done__with_log__from_different_items(self):
        task_type = random.choice(['LESSON', 'QUIZ', 'PROJECT', 'EXERCISE'])
        task = {
            'task_status': 'DONE',
            'task_type': task_type,
        }
        cohort_user = {
            'history_log': {
                'delivered_assignments': [
                    {
                        'id': 3,
                        'type': task_type,
                    },
                ],
                'pending_assignments': [
                    {
                        'id': 2,
                        'type': task_type,
                    },
                ],
            }
        }
        model = self.bc.database.create(task=task, cohort_user=cohort_user)

        Logger.info.call_args_list = []

        set_cohort_user_assignments.delay(1)

        self.assertEqual(self.bc.database.list_of('assignments.Task'), [self.bc.format.to_dict(model.task)])
        self.assertEqual(self.bc.database.list_of('admissions.CohortUser'), [
            {
                **self.bc.format.to_dict(model.cohort_user),
                'history_log': {
                    'delivered_assignments': [
                        {
                            'id': 3,
                            'type': task_type,
                        },
                        {
                            'id': 1,
                            'type': task_type,
                        },
                    ],
                    'pending_assignments': [
                        {
                            'id': 2,
                            'type': task_type,
                        },
                    ],
                },
            },
        ])
        self.assertEqual(Logger.info.call_args_list, [
            call('Executing set_cohort_user_assignments'),
            call('History log saved'),
        ])
        self.assertEqual(Logger.error.call_args_list, [])
