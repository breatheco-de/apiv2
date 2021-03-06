"""
Headers mixin
"""

import re
from datetime import datetime, tzinfo, timedelta

class simple_utc(tzinfo):
    def tzname(self,**kwargs):
        return "UTC"
    def utcoffset(self, dt):
        return timedelta(0)

class DatetimeMixin():
    """Headers mixin"""

    def datetime_to_iso(self, date=datetime.utcnow()) -> str:
        return re.sub(
            r'\+00:00$', 'Z',
            date.replace(tzinfo=simple_utc()).isoformat()
        )

    def assertDatetime(self, date):
        if not isinstance(date, str):
            self.assertTrue(isinstance(date, datetime))
            return True

        try:
            string = re.sub(r'Z$', '', date)
            datetime.fromisoformat(string)
            self.assertTrue(True)
            return True
        except Exception:
            self.assertTrue(False)
