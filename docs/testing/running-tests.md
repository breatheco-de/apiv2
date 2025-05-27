# Running tests

## Run a test file

```bash
poetry run test breathecode/payments/tests/urls/tests_me_service_slug_consumptionsession_hash.py
```

### Pytest options

- `-v`: verbose
- `-vv`: more verbose
- `-s`: don't capture the stdout, useful when the test execution won't end.
- `-k`: only run test methods and classes that match the pattern or substring.

## Run tests in parallel

```bash
poetry run test:parallel
```

## Run tests in parallel in a module

```bash
poetry run test:parallel ./breathecode/
```

## Run coverage in parallel

```bash
poetry run test:coverage
```

## Run coverage in parallel in a module

```bash
poetry run test:coverage breathecode.admissions
```
