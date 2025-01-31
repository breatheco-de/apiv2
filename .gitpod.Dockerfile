# https://github.com/gitpod-io/workspace-images/blob/main/chunks/tool-postgresql/Dockerfile
FROM gitpod/workspace-python-3.13

# Dazzle does not rebuild a layer until one of its lines are changed. Increase this counter to rebuild this layer.
ENV TRIGGER_REBUILD=4
ENV PGWORKSPACE="/workspace/.pgsql"
ENV PGDATA="$PGWORKSPACE/data"

# Install PostgreSQL
RUN sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - && \
    echo "deb https://apt.llvm.org/$(lsb_release -cs)/ llvm-toolchain-$(lsb_release -cs)-18 main" | sudo tee /etc/apt/sources.list.d/llvm.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add - && \
    sudo install-packages postgresql-16 postgresql-contrib-16 redis-server netcat \
    make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget \
    curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Setup PostgreSQL server for user gitpod
ENV PATH="/usr/lib/postgresql/16/bin:$PATH"

SHELL ["/usr/bin/bash", "-c"]
RUN PGDATA="${PGDATA//\/workspace/$HOME}" \
    && mkdir -p ~/.pg_ctl/bin ~/.pg_ctl/sockets $PGDATA \
    && initdb -D $PGDATA \
    && printf '#!/bin/bash\npg_ctl -D $PGDATA -l ~/.pg_ctl/log -o "-k ~/.pg_ctl/sockets" start\n' > ~/.pg_ctl/bin/pg_start \
    && printf '#!/bin/bash\npg_ctl -D $PGDATA -l ~/.pg_ctl/log -o "-k ~/.pg_ctl/sockets" stop\n' > ~/.pg_ctl/bin/pg_stop \
    && chmod +x ~/.pg_ctl/bin/*
ENV PATH="$HOME/.pg_ctl/bin:$PATH"
ENV DATABASE_URL="postgresql://gitpod@localhost"
ENV PGHOSTADDR="127.0.0.1"
ENV PGDATABASE="postgres"
COPY --chown=gitpod:gitpod postgresql-hook.bash $HOME/.bashrc.d/200-postgresql-launch

# RUN pip install pipenv

USER gitpod

RUN rm -rf $HOME/.pyenv
RUN rm -rf /home/gitpod/.local/share/pypoetry /home/gitpod/.local/share/pipx /home/gitpod/.local/bin/poetry
RUN curl https://pyenv.run | bash

RUN pyenv update
RUN pyenv install 3.13.1 && pyenv global 3.13.1
RUN pip install pipx
RUN pipx install poetry

RUN echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
RUN echo -e 'eval "$(pyenv init --path)"\neval "$(pyenv init -)"' >> ~/.bashrc
RUN exec "$SHELL"

RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc
