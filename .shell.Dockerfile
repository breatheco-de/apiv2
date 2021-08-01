# alpine has very much issues with python
FROM python:slim

EXPOSE 8000
ENV PYTHONUNBUFFERED 1
ENV DATABASE_URL postgres://user:pass@postgres:5432/breathecode
ENV REDIS_URL redis://redis:6379

RUN echo breathecode > /etc/hostname
RUN apt-get update && \
    apt-get install gcc python3-psycopg2 libpq-dev python3-dev fish curl git sudo tmux -y && \
    apt-get clean && \
    rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

WORKDIR /tmp

RUN curl -L https://get.oh-my.fish > install && \
    fish install --noninteractive --yes && \
    rm install

WORKDIR /usr/src

COPY . .
COPY .git/ .git/

RUN python -m scripts.install

CMD ["fish"]
