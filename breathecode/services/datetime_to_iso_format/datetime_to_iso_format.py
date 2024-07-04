import re
from datetime import datetime, tzinfo, timedelta


class SimpleUTC(tzinfo):

    def tzname(self, **kwargs):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def datetime_to_iso_format(date: datetime) -> str:
    return re.sub(r"\+00:00$", "Z", date.replace(tzinfo=SimpleUTC()).isoformat())
