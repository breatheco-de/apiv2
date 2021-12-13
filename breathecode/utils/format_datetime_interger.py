import re

from datetime import datetime
from dateutil.tz import gettz, tzutc


def format_datetime_interger(timezone: str, interger: int):
    timezone = gettz(timezone)
    matches = re.match('^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$', str(interger))
    if not matches:
        return None

    elements = matches.groups()
    date = datetime(int(elements[0]),
                    int(elements[1]),
                    int(elements[2]),
                    int(elements[3]),
                    int(elements[4]),
                    tzinfo=timezone)

    return re.sub(r'\+00:00', 'Z', date.astimezone(tzutc()).isoformat())
