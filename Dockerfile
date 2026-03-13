# alpine has very much issues with python
FROM python:3.13

ENV PYTHONUNBUFFERED=1
RUN pip install poetry

WORKDIR /usr/src

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --no-root --only main
COPY . .

EXPOSE 8000
# CMD python manage.py runserver 0.0.0.0:8000
CMD python -m scripts.docker_entrypoint
