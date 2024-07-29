import logging
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


def has_duplicates(values):
    if len(values) != len(set(values)):
        return True
    else:
        return False


class CohortDayLog(object):
    current_module = None
    teacher_comments = None
    created_at = None
    attendance_ids = []
    unattendance_ids = []

    def __init__(
        self,
        current_module: str = None,
        teacher_comments: str = None,
        attendance_ids: list = None,
        unattendance_ids: list = None,
        updated_at: datetime = None,
        allow_empty=False,
    ):

        if not isinstance(current_module, str) and (not allow_empty and current_module is None):
            raise Exception(f"Invalid current module value {str(current_module)}")
        if teacher_comments is not None and not isinstance(teacher_comments, str):
            raise Exception(f"Invalid teacher comments value {str(teacher_comments)}")
        if not isinstance(attendance_ids, list):
            raise Exception("Invalid attendance list, it must be an array of integer ids")
        if not isinstance(unattendance_ids, list):
            raise Exception("Invalid unattendance list, it must be an array of integer ids")
        if updated_at is None:
            updated_at = timezone.now()

        if has_duplicates(attendance_ids):
            raise Exception("Attendance list has duplicate user ids")

        if has_duplicates(unattendance_ids):
            raise Exception("Unattendance list has duplicate user ids")

        self.current_module = current_module
        self.teacher_comments = teacher_comments
        self.attendance_ids = attendance_ids
        self.unattendance_ids = unattendance_ids
        self.updated_at = updated_at

    @staticmethod
    def empty():
        return CohortDayLog(
            **{
                "current_module": None,
                "teacher_comments": None,
                "updated_at": None,
                "attendance_ids": [],
                "unattendance_ids": [],
                "allow_empty": True,
            }
        )

    def serialize(self):
        return {
            "current_module": self.current_module,
            "teacher_comments": self.teacher_comments,
            "attendance_ids": self.attendance_ids,
            "unattendance_ids": self.unattendance_ids,
            "updated_at": str(self.updated_at),
        }


class CohortLog(object):
    days = []
    cohort = None

    def __init__(self, cohort):

        self.days = []
        self.cohort = None

        if cohort is None:
            raise Exception("Cohort log cannot be retrieved because it's null")

        self.cohort = cohort
        if self.cohort.current_day == 0:
            self.cohort.current_day = 1

        if self.cohort.history_log is None:
            self.cohort.history_log = {}

        elif not isinstance(self.cohort.history_log, dict):
            raise Exception("Cohort history json must be in dictionary format")

        for day in range(1, self.cohort.current_day + 1):
            if str(day) in self.cohort.history_log:
                self.days = [*self.days, CohortDayLog(**self.cohort.history_log[str(day)], allow_empty=True)]
            else:
                self.days = [*self.days, CohortDayLog.empty()]

    def log_day(self, payload, day=None):

        if not isinstance(payload, dict):
            raise Exception("Entry log of cohort day must be a dictionary")

        if day is None:
            day = self.cohort.current_day

        if day == 0:
            raise Exception("Invalid log for day index=0, cohort days start at 1")

        elif day > self.cohort.current_day:
            raise Exception(
                f"You cannot log activity for day {str(day)} because the cohort is currently at day {str(self.cohort.current_day)}"
            )

        try:
            self.days[day - 1] = CohortDayLog(**payload)
            logger.debug(f"Replaced cohort {self.cohort.slug} log for day {day}")
        except IndexError:
            raise Exception(f"Error adding day {str(day-1)} log to cohort")

    def save(self):

        count = 0
        for day in self.days:
            count += 1
            self.cohort.history_log[str(count)] = day.serialize()

        self.cohort.save()

    def serialize(self):
        return self.cohort.history_log
