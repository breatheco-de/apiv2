# Setup & Installation

1. Install redis, postgress, python 3.8+ and node 14+
2. Create enviroment variables `cp .env.example .env` (make sure to fill the variables with relevant values)
3. Make sure to get inside the environment: `pipenv shell`
4. Run the migrations into your database `pipenv run migrate`
5. Run the fixtures to add sample data: `pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json`
6. Make sure you can login into the django admin, you can create a login user with `python manage.py createsuperuser`

# Dumentation for BreatheCode API

[Read the docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef)

# Additional Resources

## Run the tests

```bash
docker-compose up -d
pytest
```

## Run coverage

Report in console

```bash
docker-compose up -d
pytest ./breathecode --disable-pytest-warnings --cov=breathecode --cov-report term-missing
```

Report with HTML

```bash
docker-compose up -d
pytest ./breathecode --disable-pytest-warnings --cov=breathecode --cov-report html
```

Report with XML

```bash
docker-compose up -d
pytest ./breathecode --disable-pytest-warnings --cov=breathecode --cov-report xml
```

Report with cover file

```bash
docker-compose up -d
pytest ./breathecode --disable-pytest-warnings --cov=breathecode --cov-report annotate

# remove cover files
find . -name "*.py,cover" -type f -delete
```

## Fixtures

Fixtures are fake data ideal for development.

Saving new fixtures
```bash
python manage.py dumpdata auth > ./breathecode/admissions/fixtures/users.json
```

Loading all fixtures
```bash
pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json
```

## Icons

The following icons arebeing used for the slack integrations: https://www.pngrepo.com/collection/soft-colored-ui-icons/1