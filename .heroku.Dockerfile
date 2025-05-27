FROM newrelic/infrastructure:latest as infrastructure

FROM heroku/heroku:22

COPY --from=infrastructure /usr/bin/newrelic-infra /usr/bin/newrelic-infra
COPY --from=infrastructure /usr/bin/newrelic-infra-ctl /usr/bin/newrelic-infra-ctl
COPY --from=infrastructure /usr/bin/newrelic-infra-service /usr/bin/newrelic-infra-service
COPY --from=infrastructure /newrelic /newrelic

ENV NEW_RELIC_LICENSE_KEY $NEW_RELIC_LICENSE_KEY

RUN apt update -y \
    && apt install -y -qq software-properties-common curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt update -y -qq \
    && apt upgrade -y -qq \
    && apt install -y -qq --no-install-recommends software-properties-common curl libcap2-bin \
    python3.12 python3.12-dev pip libpq-dev libboost-all-dev kmod sudo \
    && apt clean -y -qq \
    && rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN python3.12 -m pip install poetry && \
    python3.12 -m pip cache purge && \
    rm -rf $HOME/.cache/pipenv /tmp/*

RUN useradd -ms /bin/bash 4geeks

RUN mkdir /var/run/newrelic-infra
RUN mkdir /var/db
RUN mkdir /var/db/newrelic-infra
RUN mkdir /var/db/newrelic-infra/data
RUN chown -R 4geeks:4geeks /var/run/newrelic-infra
RUN chown -R 4geeks:4geeks /var/db/newrelic-infra
RUN chown -R 4geeks:4geeks /var/db/newrelic-infra/data

RUN touch /etc/newrelic-infra.yml
RUN chown 4geeks:4geeks /etc/newrelic-infra.yml

USER 4geeks
ENV NRIA_MODE="UNPRIVILEGED"

COPY . /app
WORKDIR /app

ENV NEW_RELIC_APP_NAME ${NEW_RELIC_APP_NAME}
ENV NEW_RELIC_LICENSE_KEY ${NEW_RELIC_LICENSE_KEY}
ENV NEW_RELIC_LOG ${NEW_RELIC_LOG}
ENV NEW_RELIC_API_KEY ${NEW_RELIC_API_KEY}
ENV NEW_RELIC_ACCOUNT_ID ${NEW_RELIC_ACCOUNT_ID}
ENV NRIA_LICENSE_KEY ${NEW_RELIC_LICENSE_KEY}

RUN echo $NEW_RELIC_LICENSE_KEY
RUN echo ${NEW_RELIC_LICENSE_KEY}

RUN poetry install --no-root --no-dev && \
    python3.12 -m pip cache purge && \
    rm -rf $HOME/.cache/pipenv /tmp/*

# RUN newrelic-infra
