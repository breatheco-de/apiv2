import re

from datetime import datetime
from dateutil.tz import gettz, tzutc
from dateutil import parser
import pytz


class Datetime(datetime):

    def __setattr__(self, key, value):
        if key == 'info':
            object.__setattr__(self, key, value)
        else:
            super(Datetime, self).__setattr__(key, value)


class DatetimeInteger:

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
