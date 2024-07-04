"""
Format date to common rest format
"""

import re
from datetime import datetime, date

__all__ = ["DateFormatterMixin"]


class DateFormatterMixin:
    """Setup ENV variable"""

    def date_today(self):
        """get current date"""
        return date.today()

    def date_today_to_iso_format(self, literal=None):
        """get current date with iso format"""
        current = literal if literal else self.date_today()
        return re.sub(r"\+00:00$", "Z", current.isoformat())

    def datetime_iso_format_to_date_string(self, current: str):
        """get current date with iso format"""
        return current.split("T")[0]

    def datetime_today(self):
        """get current datetime"""
        return datetime.today()

    def datetime_today_to_iso_format(self, literal=None):
        """get current datetime with iso format"""
        current = literal if literal else self.datetime_today()
        return re.sub(r"\+00:00$", "Z", current.isoformat())
