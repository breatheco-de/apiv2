FROM gitpod/workspace-postgres:latest

RUN sudo apt-get update \
    && sudo apt-get update \
    && sudo apt-get install -y redis-server \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN echo $'#!/bin/env python\
\
import os\
import re\
import subprocess\
\
command = \'git status --porcelain\'\
path = \'/home/gitpod/.pyenv\'\
\
os.chdir(path)\
\
\
def get_path(s):\
    result = s.split(' ')\
    print('line')\
    if result:\
        return result[-1]\
\
    return ''\
\
\
output = [\
    get_path(x) for x in subprocess.check_output([\'git\', \'status\', \'--porcelain\']).decode(\'utf-8\').split(\'\n\')\
    if x\
]\
\
for file in output:\
    os.remove(file)\
\
print('done!')\
' >> ./fix_pyenv.py

RUN python ./fix_pyenv.py
RUN pyenv update && pyenv install 3.10.7 && pyenv global 3.10.7
RUN pip install pipenv yapf

# remove PIP_USER environment
USER gitpod
RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc
