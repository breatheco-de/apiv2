# Testing

## Run tests

```bash
pipenv run test ./breathecode/
```

## Run coverage

```bash
pipenv run cov breathecode
```

## Testing inside Docker (fallback option)

1. Check which dependencies you need install in you operating system `pipenv run doctor` or `python -m scripts.doctor`.
2. Instal [docker desktop](https://www.docker.com/products/docker-desktop) in you use Windows else find a guide to install Docker and Docker Compose in your linux distribution `uname -a`.
3. Generate the BreatheCode Shell image with `pipenv run docker_build_shell`.
4. Run BreatheCode Shell with `docker-compose run bc-shell`
5. Run `pipenv run test` or `pipenv run cov`.
