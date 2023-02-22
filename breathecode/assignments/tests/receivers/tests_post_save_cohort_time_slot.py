from datetime import timedelta
import random
from unittest.mock import MagicMock, call, patch

from breathecode.assignments import tasks
from django.utils import timezone
from ..mixins import AssignmentsTestCase

UTC_NOW = timezone.now()


class MediaTestSuite(AssignmentsTestCase):
    """
    🔽🔽🔽 With zero Cohort
    """

    @patch('breathecode.assignments.tasks.set_cohort_user_assignments.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_without_cohorts(self):
        self.assertEqual(self.bc.database.list_of('events.LiveClass'), [])
        self.assertEqual(tasks.set_cohort_user_assignments.delay.call_args_list, [])

    """
    🔽🔽🔽 With two Task
    """

    @patch('breathecode.assignments.tasks.set_cohort_user_assignments.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_with_two_tasks__without_change_task_status(self):
        model = self.bc.database.create(task=2)

        model.task[0].title = self.bc.fake.name()[:150]
        model.task[0].save()

        model.task[1].title = self.bc.fake.name()[:150]
        model.task[1].save()

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         self.bc.database.list_of('admissions.Cohort'))
        self.assertEqual(tasks.set_cohort_user_assignments.delay.call_args_list, [])

    @patch('breathecode.assignments.tasks.set_cohort_user_assignments.delay', MagicMock())
    @patch('django.utils.timezone.now', MagicMock(return_value=UTC_NOW))
    def test_with_two_tasks__changing_task_status(self):
        statuses = ['PENDING', 'DONE']
        task = [{'task_status': random.choice(statuses)} for _ in range(2)]
        model = self.bc.database.create(task=task)

        model.task[0].task_status = 'DONE' if model.task[0].task_status == 'PENDING' else 'PENDING'
        model.task[0].save()

        model.task[1].task_status = 'DONE' if model.task[1].task_status == 'PENDING' else 'PENDING'
        model.task[1].save()

        self.assertEqual(self.bc.database.list_of('admissions.Cohort'),
                         self.bc.database.list_of('admissions.Cohort'))
        self.assertEqual(tasks.set_cohort_user_assignments.delay.call_args_list, [call(1), call(2)])
