import os
from datetime import date, datetime, time
from functools import cache
from typing import Optional

import pytz
from babel.dates import format_date as babel_format_date
from babel.dates import format_datetime as babel_format_datetime
from babel.dates import format_time as babel_format_time
from babel.dates import format_timedelta as babel_format_timedelta

__all__ = ['translation', 'format_date', 'format_datetime', 'format_time', 'format_timedelta']

IS_TEST_ENV = os.getenv('ENV') == 'test'


def get_short_code(code: str) -> str:
    return code[:2]


def format_and_assert_code(code: str, from_kwargs: bool = False) -> None:
    # do not remove the assertions

    is_short = len(code) == 2
    print('code', code)
    print('is_short', is_short)

    # first two character only with lowercase
    print('code[:2]', code[:2])
    assert code[:2].islower()

    # last two character only with lowercase
    if not is_short and from_kwargs:
        print('code[3:]', code[3:])
        assert code[3:].islower()

    # last two character only with uppercase
    elif not is_short:
        print('code[2:]', code[2:])
        assert code[2:].isupper()

    separator = '_' if from_kwargs else '-'

    #the format is en or en-US
    assert len(code) == 2 or (len(code) == 5 and code[2] == separator)

    if not from_kwargs:
        return code.replace(separator, '_')

    return code


# parse a date to a str with the local format
def format_date(code: str, date: date, format='medium'):
    """Translate the date to the local language"""

    code = format_and_assert_code(code)
    return babel_format_date(date, locale=code, format=format)


# parse a date to a str with the local format
def format_datetime(code: str, date: datetime, tz: pytz.BaseTzInfo | str = pytz.UTC, format='medium'):
    """Translate the datetime to the local language"""

    code = format_and_assert_code(code)

    if isinstance(tz, str):
        tz = pytz.timezone(tz)

    return babel_format_datetime(date, locale=code, tzinfo=tz, format=format)


def format_time(code: str, date: time, format='full', **kwargs: str):
    """Translate the time to the local language"""

    code = format_and_assert_code(code)
    return babel_format_time(date, locale=code, format=format)


def format_timedelta(code: str, date: time):
    """Translate the timedelta to the local language"""

    code = format_and_assert_code(code)
    return babel_format_timedelta(date, locale=code)


@cache
def translation(code: str, slug: Optional[str] = None, **kwargs: str) -> str:
    """Get the translation"""

    code = format_and_assert_code(code)

    # do the assertions
    for key in kwargs:
        format_and_assert_code(key, from_kwargs=True)

    # the english if mandatory
    assert 'en' in kwargs or 'en_us' in kwargs

    if slug and IS_TEST_ENV:
        return slug

    is_short = len(code) == 2

    if code in kwargs:
        return kwargs[code]

    elif not is_short and (short_code := get_short_code(code)) in kwargs:
        return kwargs[short_code]

    elif 'en_us' in kwargs:
        return kwargs['en_us']

    return kwargs['en']
