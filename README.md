<h1 align="center"> 
  <br>
  <a href="https://breatheco.de/"><img src="https://raw.githubusercontent.com/breatheco-de/apiv2/main/breathecode/static/assets/logo.png" alt="4Geeks" width="128"></a>
  <br>
</h1>

<h4 align="center">4Geeks's mission is to <b>accelerate the way junior developers learn and evolve</b> using technology.</h4>

<p align="center">
  <a href="https://coveralls.io/github/breatheco-de/apiv2">
    <img src="https://img.shields.io/coveralls/github/breatheco-de/apiv2"
         alt="Coveralls">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/dockerhub.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/checks.yml/badge.svg"
         alt="Checks">
  </a>
</p>

## Documentation

You can find the development documentation [on the website](https://breatheco-de.github.io/apiv2/).

Check out the [Postman docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef), [Swagger](https://breathecode.herokuapp.com/swagger/) or [Redoc](https://breathecode.herokuapp.com/swagger/).

The documentation is divided into several sections:


-   [Run 4Geeks in Codespaces (no installation)](#run-4geeks-in-codespaces-no-instalation)
-   [Install Docker](#install-docker)
-   [Run 4Geeks API as docker service](#run-4geeks-api-as-docker-service)
-   [Run 4Geeks in your local machine](#run-4geeks-api-in-your-local-machine)
    -   [Installation](#installation)
    -   [Run 4Geeks API](#run-4geeks-api)
-   [Run tests](#run-tests)

## Run 4Geeks in Codespaces (no installation)

Click `Code` -> `Codespaces` -> `Create namespace on {BRANCH_NAME}`.

![Codespaces](docs/images/codespaces.png)

## Install Docker

Install [docker desktop](https://www.docker.com/products/docker-desktop) in your Windows, else find a guide to install Docker and Docker Compose in your linux distribution `uname -a`.

## Running 4geeks

### `Run 4Geeks API as docker service`

```bash
# open 4Geeks API as a service and export the port 8000
docker-compose up -d

# create super user
sudo docker compose run 4geeks python manage.py createsuperuser

# See the output of Django
docker-compose logs -f 4geeks

# open localhost:8000 to view the api
# open localhost:8000/admin to view the admin
```

### `Run 4Geeks in your local machine`

#### Installation

```bash
# Check which dependencies you need install in your operating system
python -m scripts.doctor

# Setting up the redis and postgres database, you also can install manually in your local machine this databases
docker-compose up -d redis postgres

# Install and setting up your development environment (this command replace your .env file)
python -m scripts.install
```

#### Run 4Geeks API

You must up Redis and Postgres before open 4Geeks.

```bash
# Collect statics
pipenv run python manage.py collectstatic --noinput

# Run migrations
pipenv run python manage.py migrate

# Load fixtures (populate the database)
pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json

# Create super user
pipenv run python manage.py createsuperuser

# Run server
pipenv run start

# open localhost:8000 to view the api
# open localhost:8000/admin to view the admin
```

### `Testing in your local machine`

#### Installation

```bash
# Check which dependencies you need install in your operating system
python -m scripts.doctor

# Install and setting up your development environment (this command replace your .env file)
python -m scripts.install
```

#### Run tests

```bash
# Testing
pipenv run test ./breathecode/activity  # path

# Testing in parallel
pipenv run ptest ./breathecode/activity  # path

# Coverage
pipenv run cov breathecode.activity  # python module path

# Coverage in parallel
pipenv run pcov breathecode.activity  # python module path
```
