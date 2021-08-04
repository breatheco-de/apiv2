<h1 align="center">
  <br>
  <a href="https://breatheco.de/"><img src="https://assets.breatheco.de/apis/img/images.php?blob&random&cat=icon&tags=breathecode,128" alt="BreatheCode" width="128"></a>
  <br>
  BreatheCode
  <br>
</h1>

<h4 align="center">BreatheCode's mission is to <b>accelerate the way junior developers learn and evolve</b> using technology.</h4>

<p align="center">
  <a href="https://coveralls.io/github/breatheco-de/apiv2">
    <img src="https://img.shields.io/coveralls/github/breatheco-de/apiv2"
         alt="Coveralls">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/dockerhub.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/dockerhub.yml/badge.svg"
         alt="Docker Hub">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/linter.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/linter.yml/badge.svg"
         alt="Linter">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/test.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/test.yml/badge.svg"
         alt="Test">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/github-pages.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/github-pages.yml/badge.svg"
         alt="Test">
  </a>
</p>

## Documentation

You can find the development documentation [on the webside](https://breatheco-de.github.io/apiv2/).

Check out the [Postman docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef), [Swagger](https://breathecode.herokuapp.com/swagger/) or [Redoc](https://breathecode.herokuapp.com/swagger/).

The documentation is divided into several sections:

- [Working inside Docker (slower)](#working-inside-docker-slower)
  - [Build BreatheCode Dev docker image](#build-breathecode-dev-docker-image)
  - [Testing inside BreatheCode Dev](#testing-inside-breathecode-dev)
  - [Run BreatheCode API as docker service](#run-breathecode-api-as-docker-service)
- [Working in your local machine (recomended)](#working-in-your-local-machine-recomended)
  - [Installation in your local machine](#installation-in-your-local-machine)
  - [Testing in your local machine](#testing-in-your-local-machine)
  - [Run BreatheCode API in your local machine](#run-breathecode-api-in-your-local-machine)

## Working inside Docker (slower)

### `Build BreatheCode Dev docker image`

Instal [docker desktop](https://www.docker.com/products/docker-desktop) in you use Windows else find a guide to install Docker and Docker Compose in your linux distribution `uname -a`.

```bash
# Check which dependencies you need install in you operating system
python -m scripts.doctor

# Generate the BreatheCode Dev docker image
docker-compose build bc-dev
```

### `Testing inside BreatheCode Dev`

```bash
# Open the BreatheCode Dev, this shell don't export the port 8000
docker-compose run bc-dev fish

# Testing
pipenv run test ./breathecode/activity  # path

# Coverage
pipenv run cov breathecode.activity  # python module path
```

### `Run BreatheCode API as docker service`

```bash
# open BreatheCode API as a service and export the port 8000
docker-compose up -d bc-dev

# open the BreatheCode Dev, this shell don't export the port 8000
docker-compose run bc-dev fish

# create super user
pipenv run python manage.py createsuperuser

# Close the BreatheCode Dev
exit

# See the output of Django
docker-compose logs -f bc-dev

# open localhost:8000 to view the api
# open localhost:8000/admin to view the admin
```

## Working in your local machine (recomended)

### `Installation in your local machine`

Instal [docker desktop](https://www.docker.com/products/docker-desktop) in you use Windows else find a guide to install Docker and Docker Compose in your linux distribution `uname -a`.

```bash
# Check which dependencies you need install in you operating system
python -m scripts.doctor

# Setting up the redis and postgres database, you also can install manually in your local machine this databases
docker-compose up -d redis postgres

# Install and setting up your development environment (this command replace your .env file)
python -m scripts.install
```

### `Testing in your local machine`

```bash
# Testing
pipenv run test ./breathecode/activity  # path

# Coverage
pipenv run cov breathecode.activity  # python module path
```

### `Run BreatheCode API in your local machine`

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
