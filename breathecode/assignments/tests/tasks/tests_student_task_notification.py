"""
Test /answer
"""

from unittest.mock import MagicMock, call, patch

from breathecode.assignments import signals

from ...tasks import student_task_notification
from ..mixins import AssignmentsTestCase


class MediaTestSuite(AssignmentsTestCase):
    """Test /answer"""

    """
    🔽🔽🔽 Without Task
    """

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__without_tasks(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [])
        self.assertEqual(send_email_message.call_args_list, [])
        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [call("Task not found")])
        self.assertEqual(signals.assignment_created.send_robust.call_args_list, [])

    """
    🔽🔽🔽 With Task and Cohort revision_status PENDING
    """

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__pending__with_task__with_cohort(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "PENDING"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as pending",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__pending__with_cohort__url_ends_with_slash(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "PENDING"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as pending",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__pending__with_cohort__lang_es(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "PENDING"}
        cohort = {"language": "es"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=cohort)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Tu tarea "{model.task.title}" ha sido revisada',
                        "details": "Tu tarea se ha marcado como pendiente",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    """
    🔽🔽🔽 With Task and Cohort revision_status APPROVED
    """

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__approved__with_task__with_cohort(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "APPROVED"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as approved",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__approved__with_cohort__url_ends_with_slash(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "APPROVED"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as approved",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__approved__with_cohort__lang_es(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "APPROVED"}
        cohort = {"language": "es"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=cohort)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Tu tarea "{model.task.title}" ha sido revisada',
                        "details": "Tu tarea se ha marcado como aprobada",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    """
    🔽🔽🔽 With Task and Cohort revision_status REJECTED
    """

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__rejected__with_task__with_cohort(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "REJECTED"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as rejected",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__rejected__with_cohort__url_ends_with_slash(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "REJECTED"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=1)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Your task "{model.task.title}" has been reviewed',
                        "details": "Your task has been marked as rejected",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(str(Logger.info.call_args_list), str([call("Starting student_task_notification")]))
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )

    @patch("breathecode.notify.actions.send_email_message", MagicMock())
    @patch("logging.Logger.info", MagicMock())
    @patch("logging.Logger.error", MagicMock())
    @patch("breathecode.assignments.signals.assignment_created", MagicMock())
    def test_student_task_notification__with_task__rejected__with_cohort__lang_es(self):
        from logging import Logger

        from breathecode.notify.actions import send_email_message

        task = {"revision_status": "REJECTED"}
        cohort = {"language": "es"}
        with patch("breathecode.activity.tasks.get_attendancy_log.delay", MagicMock()):
            model = self.bc.database.create(task=task, cohort=cohort)

        Logger.info.call_args_list = []

        student_task_notification.delay(1)

        self.assertEqual(self.bc.database.list_of("assignments.Task"), [self.bc.format.to_dict(model.task)])
        self.assertEqual(
            send_email_message.call_args_list,
            [
                call(
                    "diagnostic",
                    model.user.email,
                    {
                        "subject": f'Tu tarea "{model.task.title}" ha sido revisada',
                        "details": "Tu tarea se ha marcado como rechazada",
                    },
                    academy=model.academy,
                )
            ],
        )

        self.assertEqual(Logger.info.call_args_list, [call("Starting student_task_notification")])
        self.assertEqual(Logger.error.call_args_list, [])
        self.assertEqual(
            signals.assignment_created.send_robust.call_args_list,
            [call(instance=model.task, sender=model.task.__class__)],
        )
