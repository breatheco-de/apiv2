import re

from datetime import datetime
from dateutil.tz import gettz, tzutc
from dateutil import parser
import pytz

__all__ = ['DatetimeInteger', 'duration_to_str']


def duration_to_str(duration):
    if duration is None:
        return 'none'

    total_seconds = duration.seconds
    sec_value = total_seconds % (24 * 3600)
    hour_value = sec_value // 3600
    sec_value %= 3600
    min = sec_value // 60
    sec_value %= 60

    if hour_value > 0:
        msg = f'{hour_value} hr'
        if min > 0:
            msg += f', {min} min'
        if sec_value > 0:
            msg += f' and {sec_value} sec'
        return msg
    elif min > 0:
        msg = f'{min} min'
        if sec_value > 0:
            msg += f' and {sec_value} sec'
        return msg
    elif sec_value > 0:
        return f'{sec_value} sec'
    else:
        return 'none'


class Datetime(datetime):
    def __setattr__(self, key, value):
        if key == 'info':
            object.__setattr__(self, key, value)
        else:
            super(Datetime, self).__setattr__(key, value)


class DatetimeInteger:
    """This type of date pretend resolve the problems related to summer schedule"""
    def __init__(self, year, month, day, hour, minute):
        self.year = str(year)
        self.month = str(month)
        self.day = str(day)
        self.hour = str(hour)
        self.minute = str(minute)

    def get_interger(self):
        return int(self.year + self.month + self.day + self.hour + self.minute)

    def get_datetime(self, timezone: str):
        self.__class__.to_datetime(timezone, self.get_interger())

    def get_utc_datetime(self, timezone: str):
        self.__class__.to_utc_datetime(timezone, self.get_interger())

    @staticmethod
    def from_datetime(timezone: str, date: datetime) -> int:
        return int(date.astimezone(gettz(timezone)).strftime('%Y%m%d%H%M'))

    @staticmethod
    def from_iso_string(timezone: str, string: str) -> int:
        date = parser.parse(string)
        tz = gettz(timezone)

        return int(date.astimezone(tzutc()).astimezone(tz).strftime('%Y%m%d%H%M'))

    @staticmethod
    def to_iso_string(timezone: str, interger: int) -> str:
        tz = gettz(timezone)
        matches = re.match('^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$', str(interger))
        if not matches:
            return None

        elements = matches.groups()
        date = datetime(int(elements[0]),
                        int(elements[1]),
                        int(elements[2]),
                        int(elements[3]),
                        int(elements[4]),
                        tzinfo=tz)

        return re.sub(r'\+00:00', 'Z', date.astimezone(tzutc()).isoformat())

    @staticmethod
    def to_datetime(timezone: str, interger: int) -> datetime:
        tz = pytz.timezone(timezone)
        matches = re.match('^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$', str(interger))
        if not matches:
            return None

        elements = matches.groups()
        date = datetime(int(elements[0]),
                        int(elements[1]),
                        int(elements[2]),
                        int(elements[3]),
                        int(elements[4]),
                        tzinfo=tz)

        return date

    @staticmethod
    def to_utc_datetime(timezone: str, interger: int) -> datetime:
        tz = pytz.timezone(timezone)
        matches = re.match('^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$', str(interger))
        if not matches:
            return None

        elements = matches.groups()
        date = datetime(int(elements[0]),
                        int(elements[1]),
                        int(elements[2]),
                        int(elements[3]),
                        int(elements[4]),
                        tzinfo=tz)

        return date.astimezone(pytz.UTC)
