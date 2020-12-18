# Setup environment

```bash
cp .env.example .env
```

# BreatheCode API

[Read the docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef)


# Run the tests

```bash
docker-compose up -d
pytest
```

# Run coverage

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

# Fixtures

Fixtures are fake data ideal for development.

Saving new fixtures
```bash
python manage.py dumpdata auth > ./breathecode/admissions/fixtures/users.json
```

Loading all fixtures
```bash
pipenv run python manage.py loaddata breathecode/*/fixtures/dev_*.json
```