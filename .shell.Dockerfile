# alpine has very much issues with python
# FROM ubuntu:rolling
# FROM alpine
FROM python:slim

ENV PYTHONUNBUFFERED=1

# RUN pacman -Syu --noconfirm python python-pip
# RUN apk add python3 py3-pip gcc build-base --no-cache --update
# RUN apt update
# RUN apt install python3 python3-pip -y
# RUN pip install pipenv yapf

# RUN useradd -ms /bin/bash breathecode

# USER breathecode
# WORKDIR /home/breathecode/apiv2
WORKDIR /usr/src

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN apt-get update
RUN apt-get install gcc python3-psycopg2 libpq-dev python3-dev -y
RUN pip install pipenv yapf
RUN pipenv install --dev

COPY . .

# RUN ls -a
# RUN ls -a; python -m .scripts.install
