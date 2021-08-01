# alpine has very much issues with python
FROM python:slim

EXPOSE 8000

RUN echo breathecode > /etc/hostname
RUN apt-get update && \
    apt-get install gcc python3-psycopg2 libpq-dev python3-dev fish curl git sudo tmux -y && \
    apt-get clean && \
    rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

WORKDIR /tmp

RUN curl -L https://get.oh-my.fish > install && \
    fish install --noninteractive --yes && \
    rm install

# RUN useradd /usr/bin/fish shell
RUN useradd shell

USER shell
WORKDIR /home/shell/apiv2

ENV PYTHONUNBUFFERED=1
ENV PATH="${PATH}:/home/shell/.local/bin"

RUN curl -L https://get.oh-my.fish > install && \
    fish install --noninteractive --yes && \
    rm install

COPY . .
COPY .git/ .git/

RUN python -m scripts.install && \
    rm .env

CMD ["fish"]
