# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
RUN pip install poetry

WORKDIR /usr/src

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-dev
COPY . .

EXPOSE 8000
# CMD python manage.py runserver 0.0.0.0:8000
CMD python -m scripts.docker_entrypoint
