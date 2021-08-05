# Getting started

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
