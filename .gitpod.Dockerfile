FROM gitpod/workspace-postgres:latest

SHELL ["/bin/bash", "-c"]

RUN sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' \
    && wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Add LLVM repository and key
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - \
    && echo "deb https://apt.llvm.org/jammy/ llvm-toolchain-jammy-18 main" | sudo tee /etc/apt/sources.list.d/llvm.list

RUN sudo apt-get update \
    && sudo apt-get install -y redis-server postgresql \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

# RUN sudo update-alternatives --set postgresql /usr/lib/postgresql/16/bin/postgres

# RUN pyenv update && pyenv install 3.12.3 && pyenv global 3.12.3
RUN pyenv install 3.12.3 && pyenv global 3.12.3
RUN pip install pipenv

# Set up PostgreSQL 16
USER postgres
RUN /usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/16/data
RUN echo "host all all all md5" >> /var/lib/postgresql/16/data/pg_hba.conf
RUN echo "listen_addresses='*'" >> /var/lib/postgresql/16/data/postgresql.conf
RUN /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/data start && \
    /usr/lib/postgresql/16/bin/psql -c "CREATE USER gitpod WITH PASSWORD 'gitpod';" && \
    /usr/lib/postgresql/16/bin/psql -c "ALTER USER gitpod WITH SUPERUSER;" && \
    /usr/lib/postgresql/16/bin/psql -c "CREATE DATABASE gitpod OWNER gitpod;" && \
    /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/data stop

# remove PIP_USER environment
USER gitpod

# Ensure PostgreSQL 16 is used
RUN echo "export PATH=/usr/lib/postgresql/16/bin:$PATH" >> /home/gitpod/.bashrc

RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc
