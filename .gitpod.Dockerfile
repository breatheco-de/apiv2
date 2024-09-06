# https://github.com/gitpod-io/workspace-images/blob/main/chunks/tool-postgresql/Dockerfile
# FROM gitpod/workspace-base:latest
from gitpod/workspace-python-3.12

# Dazzle does not rebuild a layer until one of its lines are changed. Increase this counter to rebuild this layer.
ENV TRIGGER_REBUILD=4
ENV PGWORKSPACE="/workspace/.pgsql"
ENV PGDATA="$PGWORKSPACE/data"

# Install PostgreSQL
RUN sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - && \
    echo "deb https://apt.llvm.org/$(lsb_release -cs)/ llvm-toolchain-$(lsb_release -cs)-18 main" | sudo tee /etc/apt/sources.list.d/llvm.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add - && \
    sudo install-packages postgresql-16 postgresql-contrib-16 redis-server

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

# # RUN pyenv update && pyenv install 3.12.3 && pyenv global 3.12.3
# RUN pyenv install 3.12.3 && pyenv global 3.12.3
# RUN pip install pipenv

USER gitpod

RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc


####


# FROM gitpod/workspace-postgres:latest

# SHELL ["/bin/bash", "-c"]

# RUN sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' \
#     && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# # Add LLVM repository and key
# RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - \
#     && echo "deb https://apt.llvm.org/jammy/ llvm-toolchain-jammy-18 main" | sudo tee /etc/apt/sources.list.d/llvm.list

# # RUN sudo apt-get update \
# #     && sudo apt-get install -y redis-server postgresql \
# #     && sudo apt-get clean \
# #     && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

# RUN sudo apt-get remove -y postgresql-12 && sudo apt-get autoremove -y
# RUN sudo install-packages redis-server postgresql postgresql-contrib

# # RUN sudo update-alternatives --set postgresql /usr/lib/postgresql/16/bin/postgres

# # RUN pyenv update && pyenv install 3.12.3 && pyenv global 3.12.3
# RUN pyenv install 3.12.3 && pyenv global 3.12.3
# RUN pip install pipenv

# # Set up PostgreSQL 16
# USER postgres
# RUN /usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/16/data
# RUN echo "host all all all md5" >> /var/lib/postgresql/16/data/pg_hba.conf
# RUN echo "listen_addresses='*'" >> /var/lib/postgresql/16/data/postgresql.conf
# RUN /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/data start && \
#     /usr/lib/postgresql/16/bin/psql -c "CREATE USER gitpod WITH PASSWORD 'gitpod';" && \
#     /usr/lib/postgresql/16/bin/psql -c "ALTER USER gitpod WITH SUPERUSER;" && \
#     /usr/lib/postgresql/16/bin/psql -c "CREATE DATABASE gitpod OWNER gitpod;" && \
#     /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/data stop

# USER root

# # remove postgresql 12
# RUN rm /usr/lib/postgresql/12 -rf

# # backup postgresql 16 settings
# # RUN mkdir /tmp/databk
# # RUN cp /workspace/.pgsql/data/postgresql.conf /tmp/databk/postgresql.conf
# # RUN cp /workspace/.pgsql/data/pg_hba.conf /tmp/databk/pg_hba.conf

# # create new data folder
# RUN rm /workspace/.pgsql/data -rf
# USER gitpod
# RUN /usr/lib/postgresql/16/bin/initdb -D /workspace/.pgsql/data

# USER root

# # restore postgresql 16 settings
# # RUN cp /tmp/databk/postgresql.conf /workspace/.pgsql/data/postgresql.conf
# # RUN cp /tmp/databk/databk/pg_hba.conf /workspace/.pgsql/data/pg_hba.conf

# # remove postgresql 16 backup folder
# # RUn rm /workspace/.pgsql/datapk -rf

# # remove PIP_USER environment
# USER gitpod

# # Ensure PostgreSQL 16 is used
# RUN echo "export PATH=/usr/lib/postgresql/16/bin:$PATH" >> /home/gitpod/.bashrc

# RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
# RUN echo "" >> $HOME/.bashrc
# RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
# RUN echo "export DATABASE_URL" >> $HOME/.bashrc
