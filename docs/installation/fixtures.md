# Fixtures

Fixtures are fake data ideal for development.

## Saving new fixtures

```bash
python manage.py dumpdata auth > ./breathecode/authenticate/fixtures/users.json
```

## Loading all fixtures

```bash
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
```
