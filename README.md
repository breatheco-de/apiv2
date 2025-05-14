<h1 align="center">
  <br>
  <a href="https://breatheco.de/"><img src="https://raw.githubusercontent.com/breatheco-de/apiv2/main/breathecode/static/assets/logo.png" alt="4Geeks" width="128"></a>
  <br>
</h1>

<h4 align="center">4Geeks's mission is to <b>accelerate the way junior developers learn and evolve</b> using technology.</h4>

<p align="center">
  <a href="https://coveralls.io/github/breatheco-de/apiv2">
    <img src="https://img.shields.io/coveralls/github/breatheco-de/apiv2"
         alt="Coveralls">
  </a>

  <a href="https://github.com/breatheco-de/apiv2/actions/workflows/dockerhub.yml">
    <img src="https://github.com/breatheco-de/apiv2/actions/workflows/checks.yml/badge.svg"
         alt="Checks">
  </a>
</p>

## Documentation

You can find the development documentation [on the website](https://breatheco-de.github.io/apiv2/).

Check out the [Postman docs](https://documenter.getpostman.com/view/2432393/T1LPC6ef), [Swagger](https://breathecode.herokuapp.com/swagger/) or [Redoc](https://breathecode.herokuapp.com/swagger/).

For Cursor IDE users, check the [docs.md](./docs.md) file which contains documentation links that can be accessed using the `@docs` symbol.

The documentation is divided into several sections:

- [Development Environments](#development-environments)
  - [GitHub Codespaces (Recommended, No Local Setup)](#github-codespaces-recommended-no-local-setup)
  - [Local Dev Container (Requires Docker)](#local-dev-container-requires-docker)

## Development Environments

Choose one of the following methods to set up your development environment. Codespaces or a Local Dev Container are recommended for consistency.

### GitHub Codespaces (Recommended for beginners and low-resource machines)

This is the easiest way to get started, especially if you have a less powerful machine or want to avoid local setup complexities. GitHub Codespaces provides a fully configured cloud-based development environment, accessible directly through your browser or via VS Code/Cursor.

1.  Navigate to the main page of the repository on GitHub.
2.  Click the `Code` button.
3.  Go to the `Codespaces` tab.
4.  Click `Create codespace on main` (or your desired branch).

GitHub will set up the environment based on the `.devcontainer` configuration in the repository. Once ready, you'll have VS Code/Cursor running in your browser (or connected locally) with all dependencies and tools installed.

**Important Note:** Due to potential timing issues with Codespaces setup (`postStartCommand`), the background services (like the database) might not start automatically. After your Codespace has loaded, open a terminal and run `docker compose up -d redis postgres` (or simply `docker compose up -d` to ensure all services defined in the compose file are running) to ensure the necessary services are available before running the API.

![Codespaces](docs/images/codespaces.png)

#### Changing Codespace Machine Type

If you find that the default Codespace machine type is too slow or you need more resources (CPU, RAM, Storage), you can change it:

*   **When creating a new Codespace:** Before clicking "Create codespace", click on the three dots (...) next to the button or the "Advanced options" link (the UI may vary slightly). This will allow you to select a more powerful machine type.
*   **For an existing Codespace:** You can change the machine type for an existing Codespace. Go to your list of Codespaces on GitHub (github.com/codespaces). Click the three dots (...) next to the Codespace you want to change, select "Change machine type", and choose a new one. The Codespace will then need to be reopened or rebuilt to apply the changes.

Using a more powerful machine type may incur higher costs if you are outside of the free tier for GitHub Codespaces.

### Local Dev Container (Requires Docker)

If you prefer to work locally, have a reasonably powerful machine, and want the same consistent environment as Codespaces, you can use VS Code/Cursor Dev Containers.

**Prerequisites:**

1.  **Docker Desktop:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your operating system.
2.  **VS Code or Cursor:** Install [Visual Studio Code](https://code.visualstudio.com/) or [Cursor](https://cursor.sh/).
3.  **Install the Dev Containers Extension:** You **must** install the official [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) from the marketplace in VS Code/Cursor.

**Windows Users (Important):**

*   You **MUST** use **WSL 2 (Windows Subsystem for Linux)**. Dev Containers rely on a Linux environment.
*   **Install WSL:** Follow the official [Microsoft guide to install WSL](https://learn.microsoft.com/en-us/windows/wsl/install). We recommend installing the **Ubuntu** distribution when prompted.
*   **Configure Docker Desktop:** Ensure Docker Desktop is configured to use the WSL 2 backend. Go to Docker Desktop settings -> Resources -> WSL Integration and enable it for your chosen distribution (e.g., Ubuntu).
*   **Clone Project in WSL:** Clone this repository *inside* your WSL environment (e.g., in `/home/<your-username>/dev/apiv2` within Ubuntu), **not** on your Windows C: drive. You can access the WSL terminal by typing `wsl` or `ubuntu` in your Windows Terminal or Command Prompt.

**Steps to Launch:**

1.  Clone this repository to your local machine (inside WSL if on Windows).
2.  Open the cloned repository folder in VS Code or Cursor (`code .` or `cursor .` from the terminal inside the project directory).
3.  Your editor should automatically detect the `.devcontainer` configuration and prompt you to "Reopen in Container". Click it.
4.  If it doesn't prompt, open the command palette (`Ctrl+Shift+P` or `Cmd+Shift+P`) and run `Dev Containers: Reopen in Container`.

VS Code or Cursor will build the Docker image (if not already built) and start the container. Your VS Code or Cursor window will then be connected to the containerized environment, complete with all dependencies.

## Available Commands (via `poetry run`)

The following custom commands are defined in `pyproject.toml` under `[tool.poetry.scripts]` and can be run using `poetry run <command>`:

*   `dev`: (Legacy or specific development task - check `scripts/cmd.py` for details)
*   `start`: Starts the Django development server.
*   `createsuperuser`: Runs Django's `createsuperuser` management command.
*   `test`: Runs `pytest` for the specified path/module.
*   `test:ci`: Runs tests with coverage specifically for CI environments (likely includes parallel execution).
*   `test:coverage` / `test:c`: Runs tests with coverage reporting for the specified module.
*   `test:parallel` / `test:p`: Runs tests in parallel using `pytest-xdist` for the specified path/module.
*   `startapp`: Runs Django's `startapp` management command to create a new app structure.
*   `migrate`: Runs Django's `migrate` management command to apply database migrations.
*   `makemigrations`: Runs Django's `makemigrations` management command to create new migration files based on model changes.
*   `format`: Formats the code using tools like `black` and `isort`.
*   `celery`: Starts a Celery worker.
*   `docs`: Serves the documentation locally using `mkdocs serve`.
*   `docs:build`: Builds the static documentation site using `mkdocs build`.
*   `docs:deploy`: Deploys the documentation (likely to GitHub Pages) using `mkdocs gh-deploy`.
*   `lint`: Runs linters (like `flake8`) over the codebase.
*   `update-sql-keywords`: Updates a JSON file containing SQL keywords (utility script).
*   `precommit:install`: Installs pre-commit hooks.
*   `docker:build`: Builds the Docker image for the application.
