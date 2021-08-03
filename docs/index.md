# Getting started

## Setup & Installation with Docker (recomended)

1. Check which dependencies you need install in you operating system `pipenv run doctor` or `python -m scripts.doctor`.
2. Instal [docker desktop](https://www.docker.com/products/docker-desktop) in your computer.
3. Install packages and configure your development environment `python -m scripts.install` (this script replace your `.env`).
4. Run containers with `docker-compose up -d redis postgres`
5. Congratulations!! You API must be running, with the migrations applied and everything.
6. If you need to run any specific command always prepend `docker-compose exec breathecode` to it, followed by your command, for example:
   6.You can create a login user with `docker-compose exec breathecode python manage.py createsuperuser`

## Setup & Installation (without Docker)

1. Check which dependencies you need install in you operating system `pipenv run doctor` or `python -m scripts.doctor`.
2. Manually install redis, postgress, python 3.9+ and node 14+.
3. Install packages and configure your development environment `python -m scripts.install` (this script replace your `.env`).
4. Run the migrations into your database `pipenv run migrate`
5. Run the fixtures to add sample data: `pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json`
6. Make sure you can login into the django admin, you can create a login user with `python manage.py createsuperuser`
7. Enable pre-commit library: `pipenv run pre-commit install` (this library helps prevent longer error wait times and get instant feedbackpipe)
