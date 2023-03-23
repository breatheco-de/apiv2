# alpine has very much issues with python
FROM mcr.microsoft.com/devcontainers/python:3

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y redis-server postgresql postgresql-contrib ca-certificates curl gnupg lsb-release \
    && apt-get clean \
    && rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh ./get-docker.sh

RUN pip install pipenv

# WORKDIR /usr/src



COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile
COPY . .
