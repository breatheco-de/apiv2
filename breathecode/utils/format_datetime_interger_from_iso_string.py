from dateutil.tz import gettz, tzutc
from dateutil import parser


def format_datetime_interger_from_iso_string(timezone: str, string: str):
    date = parser.parse(string)
    tz = gettz(timezone)

    return int(date.astimezone(tzutc()).astimezone(tz).strftime('%Y%m%d%H%M'))
