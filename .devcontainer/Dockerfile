# alpine has so much issues with python
FROM mcr.microsoft.com/devcontainers/python:3

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y redis-server postgresql postgresql-contrib ca-certificates curl gnupg lsb-release \
    && apt-get clean \
    && rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh ./get-docker.sh

RUN pip install poetry pipx

# WORKDIR /usr/src



COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock

RUN poetry install
COPY . .
