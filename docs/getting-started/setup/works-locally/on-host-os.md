# Works on host Operative System

This is the faster option because it runs directly on your machine without any extra layer that adds some latency compared with this option, but should have a problem that you would have to fix manually.

See [what is an Operative System](https://en.wikipedia.org/wiki/Operating_system).

## Set up 4geeks dependencies

Read [this](./introduction.md).

## Set up Python dependencies

We have a script with a lot of hooks to try to fix many issues that could happen during the installation

```bash
python -m scripts.install
```

## Start the server

### Collect statics

Load the public files in Django, which it requires to open the Django Admin.

```bash
poetry run python manage.py collectstatic --noinput
```

### Run migrations

#### What is a migration?

Read [this](https://en.wikipedia.org/wiki/Schema_migration).

#### Run the migrations

```bash
poetry run python manage.py migrate
```

### Populate the database

You should populate your database with initial data using:

```bash
poetry run python manage.py loaddata breathecode/*/fixtures/dev_*.json
```

### Create a super user

To get in Django Admin you need to create an account, this account will be saved in Postgres.

```bash
poetry run python manage.py createsuperuser
```

### Run server

To open the server run:

```bash
poetry run start
```

If something goes wrong execute this to get a diagnosis.

```bash
python -m scripts.doctor
```
