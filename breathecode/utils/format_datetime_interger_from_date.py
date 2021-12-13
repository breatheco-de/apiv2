from datetime import datetime


def format_datetime_interger_from_date(timezone: str, date: datetime):
    return int(date.strftime('%Y%m%d%H%M'))
