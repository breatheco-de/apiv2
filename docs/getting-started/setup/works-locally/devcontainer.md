# Devcontainer

[Devcontainer](https://code.visualstudio.com/docs/devcontainers/containers) provides you with a way to run this project on your local machine without setting any configuration.

## Set up 4geeks dependencies

Read [this](./introduction.md).

#### Can I use Podman to run Devcontainer?

Yes, but you should have compatibility issues.

#### Run Docker on non-root users

Devcontainer requires be able to run Docker on non-root users, [Follow this intructions](https://docs.docker.com/engine/install/linux-postinstall/).

## Open Devcontainer

1. Click Visual Studio Button.
2. Click reopen in Container.
3. Wait until Devcontainer tab in finished its job.

### Visual Studio Button

![Visual Studio Button](../../../images/vs-button.png)

# Local Dev Container

If you prefer to work locally, have a reasonably powerful machine, and want the same consistent environment as Codespaces, you can use VS Code/Cursor Dev Containers.

This method uses Docker to create an isolated environment with all necessary dependencies and configurations, based on the `.devcontainer` definition in the repository.

## Prerequisites

1.  **Docker Desktop:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for your operating system.
2.  **VS Code or Cursor:** Install [Visual Studio Code](https://code.visualstudio.com/) or [Cursor](https://cursor.sh/).
3.  **Install the Dev Containers Extension:** You **must** install the official [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) from the marketplace in VS Code/Cursor.

## Windows Users (Important Setup)

*   You **MUST** use **WSL 2 (Windows Subsystem for Linux)**. Dev Containers rely on a Linux environment.
*   **Install WSL:** Follow the official [Microsoft guide to install WSL](https://learn.microsoft.com/en-us/windows/wsl/install). We recommend installing the **Ubuntu** distribution when prompted.
*   **Configure Docker Desktop:** Ensure Docker Desktop is configured to use the WSL 2 backend. Go to Docker Desktop settings -> Resources -> WSL Integration and enable it for your chosen distribution (e.g., Ubuntu).
*   **Clone Project in WSL:** Clone this repository *inside* your WSL environment (e.g., in `/home/<your-username>/dev/apiv2` within Ubuntu), **not** on your Windows C: drive. You can access the WSL terminal by typing `wsl` or `ubuntu` in your Windows Terminal or Command Prompt.

## Launching the Dev Container

1.  Clone this repository to your local machine (inside WSL if on Windows).
2.  Open the cloned repository folder in VS Code or Cursor (`code .` or `cursor .` from the terminal inside the project directory).
3.  Your editor should automatically detect the `.devcontainer` configuration and prompt you to "Reopen in Container". Click it.
4.  If it doesn't prompt, open the command palette (`Ctrl+Shift+P` or `Cmd+Shift+P`) and run `Dev Containers: Reopen in Container`.

VS Code or Cursor will build the Docker image (if not already built) and start the container. Your editor window will then be connected to the containerized environment, complete with all dependencies.

For more general information, refer to the official [VS Code Dev Containers documentation](https://code.visualstudio.com/docs/devcontainers/containers).
