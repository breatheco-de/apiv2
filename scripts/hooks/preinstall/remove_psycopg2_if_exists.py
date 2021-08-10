#!/bin/env python

import os
import sys
import json
import re
from pathlib import Path

api_path = os.getcwd()
pipfile_lock_path = Path(f'{api_path}/Pipfile.lock').resolve()

with open(pipfile_lock_path, 'r') as pipfile_lock_file:
    pipfile_lock_json = json.load(pipfile_lock_file)

if 'psycopg2' in pipfile_lock_json['default']:
    del pipfile_lock_json['default']['psycopg2']

with open(pipfile_lock_path, 'w') as pipfile_lock_file:
    json.dump(pipfile_lock_json, pipfile_lock_file, indent=4)
