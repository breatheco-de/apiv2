# Running tests

## Run a test file

```bash
pipenv run test breathecode/payments/tests/urls/tests_me_service_slug_consumptionsession_hash.py
```

### Pytest options

- `-v`: verbose
- `-vv`: more verbose
- `-s`: don't capture the stdout, useful when the test execution won't end.
- `-k`: only run test methods and classes that match the pattern or substring.

## Run tests in parallel

```bash
pipenv run ptest
```

## Run tests in parallel in a module

```bash
pipenv run ptest ./breathecode/
```

## Run coverage in parallel

```bash
pipenv run pcov
```

## Run coverage in parallel in a module

```bash
pipenv run pcov breathecode.admissions
```
