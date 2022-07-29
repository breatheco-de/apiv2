# Runing tests

## Run tests

```bash
pdm run test ./breathecode/
```

## Run tests in parallel

```bash
pdm run ptest ./breathecode/
```

## Run coverage

```bash
pdm run cov breathecode
```

## Run coverage in parallel

```bash
pdm run pcov breathecode
```

## Testing inside Docker (fallback option)

1. Check which dependencies you need install in you operating system `pdm run doctor` or `python -m scripts.doctor`.
2. Install [docker desktop](https://www.docker.com/products/docker-desktop) in your Windows, else find a guide to install Docker and Docker Compose in your linux distribution `uname -a`.
3. Generate the BreatheCode Shell image with `pdm run docker_build_shell`.
4. Run BreatheCode Shell with `docker-compose run bc-shell`
5. Run `pdm run test`, `pdm run ptest`, `pdm run cov` or `pdm run pcov`.
