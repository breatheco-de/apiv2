# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
RUN pip install pdm

WORKDIR /usr/src

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pdm install --system --deploy --ignore-pipfile
COPY . .

EXPOSE 8000
# CMD python manage.py runserver 0.0.0.0:8000
CMD python -m scripts.docker_entrypoint
