import os
from datetime import date, datetime, time
from functools import cache
from typing import Optional

import pytz
from babel.dates import format_date as babel_format_date
from babel.dates import format_datetime as babel_format_datetime
from babel.dates import format_time as babel_format_time
from babel.dates import format_timedelta as babel_format_timedelta

from breathecode.utils.exceptions import MalformedLanguageCode

__all__ = ['translation', 'format_date', 'format_datetime', 'format_time', 'format_timedelta']

IS_TEST_ENV = os.getenv('ENV') == 'test'


def get_short_code(code: str) -> str:
    return code[:2]


def format_and_assert_code(code: str, from_kwargs: bool = False) -> None:
    # do not remove the assertions

    is_short = len(code) == 2

    # first two character only with lowercase
    if not code[:2].islower():
        raise MalformedLanguageCode('Lang code is not lowercase')

    print('==================')
    print('==================')
    print('==================')
    print(is_short, from_kwargs, code, code[3:].islower(), code[2:].isupper())
    print('==================')
    print('==================')
    print('==================')
    # last two character only with lowercase
    if not is_short and from_kwargs and not code[3:].islower():
        raise MalformedLanguageCode('Country code is not lowercase')

    # last two character only with uppercase
    elif not is_short and not from_kwargs and not code[2:].isupper():
        assert 0
        raise MalformedLanguageCode('Country code is not uppercase')

    separator = '_' if from_kwargs else '-'

    #the format is en or en-US
    if not (len(code) == 2 or (len(code) == 5 and code[2] == separator)):
        raise MalformedLanguageCode('Code malformed')

    if not from_kwargs:
        return code.replace(separator, '_')

    return code


# parse a date to a str with the local format
def format_date(code: Optional[str], date: date, format='medium'):
    """Translate the date to the local language"""

    if not code:
        code = 'en'

    code = format_and_assert_code(code)
    return babel_format_date(date, locale=code, format=format)


# parse a date to a str with the local format
def format_datetime(code: Optional[str],
                    date: datetime,
                    tz: pytz.BaseTzInfo | str = pytz.UTC,
                    format='medium'):
    """Translate the datetime to the local language"""

    if not code:
        code = 'en'

    code = format_and_assert_code(code)

    if isinstance(tz, str):
        tz = pytz.timezone(tz)

    return babel_format_datetime(date, locale=code, tzinfo=tz, format=format)


def format_time(code: Optional[str], date: time, format='full', **kwargs: str):
    """Translate the time to the local language"""

    if not code:
        code = 'en'

    code = format_and_assert_code(code)
    return babel_format_time(date, locale=code, format=format)


def format_timedelta(code: Optional[str], date: time):
    """Translate the timedelta to the local language"""

    if not code:
        code = 'en'

    code = format_and_assert_code(code)
    return babel_format_timedelta(date, locale=code)


def format_languages(code: str, **kwargs: str) -> list:
    """Translate the language to the local language"""

    languages = set()

    code.replace(' ', '')

    codes = [x for x in code.split(',') if x]

    for code in codes:
        priority = 1
        if ';q=' in code:
            s = code.split(';q=')
            code = s[0]
            try:
                priority = float(s[1])
            except:
                raise MalformedLanguageCode('The priority is not a float, example: "en;q=0.5"',
                                            slug='malformed-quantity-language-code')

        languages.add((priority, code))

    return [x[1] for x in sorted(languages, key=lambda x: (x[0], '-' in x[1], x[1]), reverse=True)]


def try_to_translate(code, **kwargs: str) -> str | None:
    is_short = len(code) == 2

    if code.lower() in kwargs:
        return kwargs[code.lower()]

    elif not is_short and (short_code := get_short_code(code)) in kwargs:
        return kwargs[short_code]

    return None


@cache
def translation(code: Optional[str], slug: Optional[str] = None, **kwargs: str) -> str:
    """Get the translation"""

    if not code:
        code = 'en'

    code = format_and_assert_code(code)

    # do the assertions
    for key in kwargs:
        format_and_assert_code(key, from_kwargs=True)

    # the english if mandatory
    if not ('en' in kwargs or 'en_us' in kwargs):
        raise MalformedLanguageCode('The english translation is mandatory')

    if slug and IS_TEST_ENV:
        return slug

    languages = format_languages(code)

    for language in languages:
        v = try_to_translate(language, **kwargs)

        if v:
            return v

    if 'en_us' in kwargs:
        return kwargs['en_us']

    return kwargs['en']
