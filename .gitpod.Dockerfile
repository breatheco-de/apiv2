FROM gitpod/workspace-postgres

# Redis
#   redis-server

RUN sudo apt-get update \
    && sudo apt-get update \
    && sudo apt-get install -y redis-server \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

# && sudo add-apt-repository ppa:deadsnakes/ppa \
# python3.9 python3.9-dev \
# COPY .bashrc /home/gitpod/.bashrc.txt
# RUN cat .bashrc.txt >> /home/gitpod/.bashrc

RUN pyenv update && pyenv install 3.9.4 && pyenv global 3.9.4
RUN pip install pipenv

USER gitpod
RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
