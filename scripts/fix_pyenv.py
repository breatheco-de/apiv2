#!/bin/env python

import os
import subprocess

command = 'git status --porcelain'
path = '/home/gitpod/.pyenv'

os.chdir(path)

# output = os.system(command)
output = [
    x for x in subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8').replace(
        '?? ', '').split('\n') if x
]

for file in output:
    os.remove(file)

print('done!')
