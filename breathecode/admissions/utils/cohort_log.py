import logging

logger = logging.getLogger(__name__)


def has_duplicates(values):
    if len(values) != len(set(values)):
        return True
    else:
        return False


class CohortDayLog(object):
    current_module = None
    teacher_comments = None
    attendance_ids: []

    def __init__(self, current_module: str, teacher_comments: str, attendance_ids: list):

        if not isinstance(current_module, str):
            raise Exception(f'Invalid current module value {str(current_module)}')
        if teacher_comments is not None and not isinstance(teacher_comments, str):
            raise Exception(f'Invalid teacher comments value {str(teacher_comments)}')
        if not isinstance(attendance_ids, list):
            raise Exception(f'Invalid attendance list, it must be an array of integer ids')

        if has_duplicates(attendance_ids):
            raise Exception(f'Attendance list has duplicate user ids')

        self.current_module = current_module
        self.teacher_comments = teacher_comments
        self.attendance_ids = attendance_ids

    def serialize(self):
        return {
            'current_module': self.current_module,
            'teacher_comments': self.teacher_comments,
            'attendance_ids': self.attendance_ids,
        }


class CohortLog(object):
    cohort = None
    days = []

    def __init__(self, cohort):

        if cohort is None:
            raise Exception("Cohort log cannot be retrived because it's null")

        if cohort.history_log is None:
            cohort.history_log = []
        elif not isinstance(cohort.history_log, list):
            raise Exception('Cohort history json must be in list format')

        self.cohort = cohort
        #force current day to be 1
        if self.cohort.current_day == 0:
            self.cohort.current_day = 1
        self.days = [CohortDayLog(**d) for d in self.cohort.history_log]

    def logCurrentDay(self, payload):

        if not isinstance(payload, dict):
            raise Exception('Entry log of cohort day must be a dictionary')

        try:
            if self.days[self.cohort.current_day - 2] is None:
                raise IndexError(f'Missing index {self.cohort.current_day - 2} for cohort day log')
        except IndexError as e:
            raise Exception(
                f'You are logging into the cohort for day {self.cohort.current_day} but the day {self.cohort.current_day - 1} is missing and should be filled first'
            )

        try:
            self.days[self.cohort.current_day - 1] = CohortDayLog(**payload)
            logger.debug(f'Added cohort {self.cohort.slug} log for day {self.cohort.current_day}')
        except IndexError as e:
            logger.debug(f'Replacing cohort {self.cohort.slug} log for day {self.cohort.current_day}')
            self.days.append(CohortDayLog(**payload))

    def save(self):
        self.cohort.history_log = [day.serialize() for day in self.days]
        self.cohort.save()

    def serialize(self):
        return self.cohort.history_log
