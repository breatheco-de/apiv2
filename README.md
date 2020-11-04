# Setup environment

```bash
cp .env.example .env
```

# BreatheCode API

[Read the docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef)


# Run the tests

```
DATABSE_URL=sqlite3:///tests.sqlite3 pytest --reuse-db
```