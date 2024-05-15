#!/usr/bin/env python
"""
Reminder for sending surveys to each cohort every 4 weeks
"""

# flake8: noqa: F821

import pytz

from breathecode.utils import ScriptNotification

if academy.timezone is None:
    raise ScriptNotification(f'You must set a timezone for this academy {academy.name}',
                             status='MINOR',
                             title='You must set a timezone',
                             slug='timezone-not-set')

try:
    local_tz = pytz.timezone(academy.timezone)

except pytz.exceptions.UnknownTimeZoneError:
    raise ScriptNotification(
        f'The timezone {academy.timezone} was setted for the academy {academy.name} and it\'s invalid',
        status='MINOR',
        title='You must fix your timezone',
        slug='wrong-timezone')
