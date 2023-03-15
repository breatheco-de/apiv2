# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
RUN pip install pipenv

WORKDIR /usr/src

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile
COPY . .
