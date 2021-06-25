import re
from datetime import datetime, tzinfo, timedelta


class simple_utc(tzinfo):
    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def datetime_to_iso_format(date=datetime.utcnow()) -> str:
    return re.sub(r'\+00:00$', 'Z',
                  date.replace(tzinfo=simple_utc()).isoformat())
