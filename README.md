# Setup environment

```bash
cp .env.example .env
```

# BreatheCode API

[Read the docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef)


# Run the tests

```bash
pytest
```

# Run coverage

```bash
pytest ./breathecode --disable-pytest-warnings --cov=breathecode --cov-report term-missing
```

# Fixtures

Fixtures are fake data ideal for development.

Saving new fixtures
```
python manage.py dumpdata auth > ./breathecode/admissions/fixtures/users.json
```
Loading all fixtures
```
pipenv run python manage.py loaddata breathecode/*/fixtures/*.json
```