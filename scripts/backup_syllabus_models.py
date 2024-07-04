#!/bin/env python

from __future__ import absolute_import

import os
import sys


def execute(command):
    exit_code = os.system(command)

    if exit_code:
        sys.exit(1)


STRATEGY = "bucket"
# STRATEGY = 'storage'

if __name__ == "__main__":
    print("")
    print("Backup Admissions Cohort")
    execute(f"python manage.py backup {STRATEGY} admissions Cohort")

    print("")
    print("Backup Admissions Certificate")
    execute(f"python manage.py backup {STRATEGY} admissions Certificate")

    print("")
    print("Backup Admissions Syllabus")
    execute(f"python manage.py backup {STRATEGY} admissions Syllabus")

    print("")
    print("Backup certificate Specialty")
    execute(f"python manage.py backup {STRATEGY} certificate Specialty")
