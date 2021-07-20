FROM gitpod/workspace-postgres

# Redis
#   redis-server

RUN sudo apt-get update \
    && sudo add-apt-repository ppa:deadsnakes/ppa \
    && sudo apt-get update \
    && sudo apt-get install -y redis-server python3.9 python3.9-dev \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN ls /home/gitpod/.bashrc
RUN cat /home/gitpod/.bashrc
COPY .bashrc /home/gitpod/.bashrc
RUN ls /home/gitpod/.bashrc

# RUN pyenv update && pyenv install 3.9.1 && pyenv global 3.9.1
RUN pip install pipenv
