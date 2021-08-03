# alpine has very much issues with python
FROM python:slim

EXPOSE 8000

RUN echo breathecode > /etc/hostname
RUN apt-get update && \
    apt-get install fish curl git sudo tmux vim nano -y && \
    apt-get clean && \
    rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

WORKDIR /tmp

RUN curl -L https://get.oh-my.fish > install && \
    fish install --noninteractive --yes && \
    rm install

RUN useradd shell
RUN echo 'shell     ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN usermod -s /usr/bin/fish root
RUN usermod -s /usr/bin/fish shell

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
