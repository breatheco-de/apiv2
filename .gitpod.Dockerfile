# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
RUN pip install pipenv
