# Setup environment

```bash
cp .env.example .env
```

# BreatheCode API

[Read the docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef)


# Run the tests

```
pytest
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