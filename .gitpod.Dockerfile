FROM gitpod/workspace-postgres:latest

SHELL ["/bin/bash", "-c"]

RUN sudo apt-get update \
    && sudo apt-get update \
    && sudo apt-get install -y redis-server \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*


# RUN echo "#!/bin/env python" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "import os" >> ./fix_pyenv.py
# RUN echo "import re" >> ./fix_pyenv.py
# RUN echo "import subprocess" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "command = 'git status --porcelain'" >> ./fix_pyenv.py
# RUN echo "path = '/home/gitpod/.pyenv'" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "os.chdir(path)" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "def get_path(s):" >> ./fix_pyenv.py
# RUN echo "    result = s.split(' ')" >> ./fix_pyenv.py
# RUN echo "    print('line')" >> ./fix_pyenv.py
# RUN echo "    if result:" >> ./fix_pyenv.py
# RUN echo "        return result[-1]" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "    return ''" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "output = [" >> ./fix_pyenv.py
# RUN echo "    get_path(x) for x in subprocess.check_output(['git', 'status', '--porcelain']).decode('utf-8').split('\\n')" >> ./fix_pyenv.py
# RUN echo "    if x" >> ./fix_pyenv.py
# RUN echo "]" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "for file in output:" >> ./fix_pyenv.py
# RUN echo "    os.system(f'rm -R {file}')" >> ./fix_pyenv.py
# RUN echo "" >> ./fix_pyenv.py
# RUN echo "print('done!')" >> ./fix_pyenv.py

# RUN cat ./fix_pyenv.py
# RUN python ./fix_pyenv.py

WORKDIR /home/gitpod/.pyenv
RUN git status --porcelain
RUN git reset --hard HEAD
RUN git status --porcelain
WORKDIR /home/gitpod/

RUN pyenv update && pyenv install 3.10.7 && pyenv global 3.10.7
RUN pip install pipenv yapf

# remove PIP_USER environment
USER gitpod
RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc
