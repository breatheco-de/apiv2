"""
Headers mixin
"""

import re
from datetime import UTC, datetime

from django.utils import timezone

from breathecode.utils.datetime_integer import DatetimeInteger

__all__ = ["DatetimeMixin"]


class DatetimeMixin:
    """Datetime mixin"""

    def time_to_string(self, t: datetime) -> str:
        return t.strftime("%H:%M:%S")

    def datetime_now(self) -> datetime:
        """
        Get a datetime from now with the timezone info.

        Usage:

        ```py
        self.bc.datetime.now()  # equals to '2022-03-21T07:51:55.068Z'
        ```
        """
        return timezone.now()

    def datetime_to_iso(self, date=datetime.now(UTC)) -> str:
        """
        Transform a datetime to ISO 8601 format.

        Usage:

        ```py
        utc_now = timezone.now()
        self.bc.datetime.to_iso_string(utc_now)  # equals to '2022-03-21T07:51:55.068Z'
        ```
        """
        return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=UTC).isoformat())

    def integer_to_iso(self, timezone: str, integer: int) -> str:
        return DatetimeInteger.to_iso_string(timezone, integer)

    def datetime_to_integer(self, timezone: str, date: datetime) -> str:
        return DatetimeInteger.from_datetime(timezone, date)

    def iso_to_datetime(self, iso: str) -> datetime:
        """
        Transform a ISO 8601 format to datetime.

        Usage:

        ```py
        utc_now = timezone.now()

        # equals to datetime.datetime(2022, 3, 21, 2, 51, 55, 068)
        self.bc.datetime.from_iso_string('2022-03-21T07:51:55.068Z')
        ```
        """
        string = re.sub(r"Z$", "", iso)
        date = datetime.fromisoformat(string)
        return timezone.make_aware(date)

    def datetime_to_ical(self, date=datetime.now(UTC), utc=True) -> str:
        s = f"{date.year:04}{date.month:02}{date.day:02}T{date.hour:02}{date.minute:02}{date.second:02}"
        if utc:
            s += "Z"

        return s

    def assertDatetime(self, date: datetime) -> bool:
        if not isinstance(date, str):
            self.assertTrue(isinstance(date, datetime))
            return True

        try:
            string = re.sub(r"Z$", "", date)
            datetime.fromisoformat(string)
            self.assertTrue(True)
            return True
        except Exception:
            self.assertTrue(False)
