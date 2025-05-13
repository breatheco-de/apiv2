# Available Commands

The following custom commands are defined in `pyproject.toml` under `[tool.poetry.scripts]` and can be run from within your development environment (Codespace, Dev Container, or Manual Setup with activated virtual environment) using `poetry run <command>`:

## Development Server
*   `poetry run dev`: (Legacy or specific development task - check `scripts/cmd.py` for details)
*   `poetry run start`: Starts the Django development server (usually on `http://localhost:8000`).
*   `poetry run createsuperuser`: Runs Django's interactive `createsuperuser` management command to create an admin user.
*   `poetry run startapp <app_name>`: Runs Django's `startapp` management command to create a new app structure.

## Testing
*   `poetry run test <path>`: Runs `pytest` for the specified path/module (e.g., `poetry run test ./breathecode/activity`).
*   `poetry run test:ci`: Runs tests with coverage specifically configured for CI environments.
*   `poetry run test:coverage <module>` / `poetry run test:c <module>`: Runs tests with coverage reporting for the specified Python module path (e.g., `poetry run cov breathecode.activity`).
*   `poetry run test:parallel <path>` / `poetry run test:p <path>`: Runs tests in parallel using `pytest-xdist` for the specified path/module (e.g., `poetry run ptest ./breathecode/activity`). Faster for large test suites.

## Database
*   `poetry run migrate`: Runs Django's `migrate` management command to apply database migrations.
*   `poetry run makemigrations [app_name]`: Runs Django's `makemigrations` management command to create new migration files based on model changes. Optionally specify an app name.

## Code Quality & Formatting
*   `poetry run format`: Formats the codebase using tools like `black` and `isort` according to project standards.
*   `poetry run lint`: Runs linters (like `flake8`) over the codebase to check for style issues and potential errors.
*   `poetry run precommit:install`: Installs pre-commit hooks defined in the configuration.

## Background Tasks
*   `poetry run celery`: Starts a Celery worker process for handling background tasks.

## Documentation
*   `poetry run docs`: Serves the documentation locally (usually on `http://localhost:8001`) using `mkdocs serve` for live preview.
*   `poetry run docs:build`: Builds the static documentation site into the `site/` directory using `mkdocs build`.
*   `poetry run docs:deploy`: Deploys the documentation (likely to GitHub Pages) using `mkdocs gh-deploy`.

## Utilities
*   `poetry run update-sql-keywords`: Updates a JSON file containing SQL keywords (internal utility script).
*   `poetry run docker:build`: Builds the Docker image for the application using configuration in `scripts/docker_build.py`.
