# Getting started

## Setup & Installation

1. Install redis, postgress, python 3.8+ and node 14+
2. Create environment variables `cp .env.example .env` (make sure to fill the variables with relevant values)
3. Make sure to get inside the environment: `pipenv shell`
4. Install the dependencies including development packages: `pipenv install --dev`
5. Run the migrations into your database `pipenv run migrate`
6. Run the fixtures to add sample data: `pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json`
7. Make sure you can login into the django admin, you can create a login user with `python manage.py createsuperuser`
8. Enable pre-commit library: `pipenv run install_precommit` (this library helps prevent longer error wait times and get instant feedbackpipe)

## Setup & Installation with Docker

1. Generate the Breathecode Docker image `pipenv run docker_build`
2. Create environment variables `cp .env.example .env` (make sure to fill the variables with relevant values)
3. Run containers with `docker-compose up -d`
4. Make sure you can login into the django admin, you can create a login user with `docker-compose exec breathecode python manage.py createsuperuser`
5. Enable pre-commit library: `pipenv run install_precommit` (this library helps prevent longer error wait times and get instant feedbackpipe)
