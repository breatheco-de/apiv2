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
            return self.assertTrue(isinstance(date, datetime.datetime))

        try:
            string = re.sub(r'Z$', '', date)
            datetime.fromisoformat(string)
            return self.assertTrue(True)
        except Exception:
            return self.assertTrue(False)

