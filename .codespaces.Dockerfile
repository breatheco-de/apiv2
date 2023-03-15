# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
RUN sudo mkdir -m 0755 -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

RUN sudo apt-get update \
    && sudo apt-get install -y redis-server postgresql postgresql-contrib ca-certificates curl gnupg lsb-release docker-ce docker-ce-cli \
    containerd.io docker-buildx-plugin docker-compose-plugin \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN pip install pipenv

WORKDIR /usr/src

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile
COPY . .
