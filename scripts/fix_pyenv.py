#!/bin/env python

import os
import re
import subprocess

command = 'git status --porcelain'
path = '/home/gitpod/.pyenv'

os.chdir(path)


def get_path(s):
    result = re.findall(r' (.+)$', s)
    if result:
        return result[0]

    return ''


output = [
    get_path(x) for x in subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8').split('\n')
    if x
]

for file in output:
    os.remove(file)

print('done!')
