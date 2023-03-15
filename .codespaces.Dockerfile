# alpine has very much issues with python
FROM python

ENV PYTHONUNBUFFERED=1
# RUN mkdir -m 0755 -p /etc/apt/keyrings
# RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# RUN echo \
#     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
#     $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

RUN apt-get update \
    && apt-get install -y redis-server postgresql postgresql-contrib ca-certificates curl gnupg lsb-release \
    && apt-get clean \
    && rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh ./get-docker.sh

RUN pip install pipenv

# WORKDIR /usr/src



COPY ./Pipfile ./Pipfile
COPY ./Pipfile.lock ./Pipfile.lock

RUN pipenv install --system --deploy --ignore-pipfile
COPY . .
