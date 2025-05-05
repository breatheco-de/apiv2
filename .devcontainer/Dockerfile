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

RUN pip install pipx
RUN echo "Installing poetry"
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

COPY ./.python-version ./.python-version
COPY ./pyproject.toml ./pyproject.toml

RUN poetry python install $(cat ./.python-version)
RUN poetry env use $(cat ./.python-version)

COPY ./pyproject.toml ./pyproject.toml
COPY ./poetry.lock ./poetry.lock

RUN poetry install
COPY . .
