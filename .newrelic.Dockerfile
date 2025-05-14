FROM newrelic/infrastructure:latest

RUN echo "license_key: $NEW_RELIC_LICENSE_KEY" | tee -a /etc/newrelic-infra.yml

RUN apk upgrade && \
    apk add --no-cache curl gnupg python3 python3-dev py3-pip libpq boost-dev postgresql-dev libcap py3-pip py3-numpy py3-scipy \
    musl-dev linux-headers gcc g++ cmake build-base cython libstdc++ gfortran wget freetype-dev libpng-dev openblas-dev \
    git bash jemalloc-dev autoconf zlib-dev flex bison py3-numpy py3-scipy libffi-dev openssl-dev apache-arrow && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools poetry && \
    adduser -D 4geeks && \
    mkdir -p /app

RUN ln -s /usr/include/locale.h /usr/include/xlocale.h

ARG ARROW_VERSION=14.0.1
ARG ARROW_SHA1=2ede75769e12df972f0acdfddd53ab15d11e0ac2
ARG ARROW_BUILD_TYPE=release

ENV ARROW_HOME=/usr/local \
    PARQUET_HOME=/usr/local

RUN mkdir /mnt/arrow \
    && cd /mnt/arrow \
    && curl -L -o apache-arrow-${ARROW_VERSION}.tar.gz \
    https://github.com/apache/arrow/archive/refs/tags/apache-arrow-${ARROW_VERSION}.tar.gz \
    && tar -xzvf apache-arrow-${ARROW_VERSION}.tar.gz \
    && cd arrow-apache-arrow-${ARROW_VERSION} \
    && ls

USER 4geeks
ENV NRIA_MODE="UNPRIVILEGED"

COPY . /app
WORKDIR /app

RUN python3 --version
RUN python3.12 --version

RUN poetry install --no-root --no-dev && \
    pip3 cache purge && \
    rm -rf $HOME/.cache/pipenv /tmp/*


RUN newrelic-infra


RUN newrelic profile configure --accountId $NEW_RELIC_ACCOUNT_ID --apiKey $NEW_RELIC_API_KEY && \
    /usr/bin/newrelic install -n logs-integration
#
