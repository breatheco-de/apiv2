# Works on Codespaces

## What is Codespaces?

[Codespaces](https://github.com/features/codespaces) is the cloud version of [Visual Studio Code](https://code.visualstudio.com).

### Advantages of using Codespaces

- It support all Visual Studio extensions.

### Disadvantages of using Codespaces

- The big companies hates compete, [Microsoft](https://www.microsoft.com/) injected a validation, and you cannot install or execute Pylance (and other extensions made by them) on any editor that was not released by them, even if that editor is based in Visual Studio Code, actually this is nasty and unfair, and this affect our as consumers.

## Opening your project on Codespaces

Read [this](https://github.com/features/codespaces).

# GitHub Codespaces

GitHub Codespaces is the recommended way to get started, especially for beginners or if you have a less powerful machine. It provides a fully configured cloud-based development environment, accessible directly through your browser or via VS Code/Cursor.

## Setting up a Codespace

1.  Navigate to the main page of the repository on GitHub.
2.  Click the `Code` button.
3.  Go to the `Codespaces` tab.
4.  Click `Create codespace on main` (or your desired branch).

GitHub will set up the environment based on the `.devcontainer` configuration in the repository. Once ready, you'll have VS Code/Cursor running in your browser (or connected locally) with all dependencies and tools installed.

## Important Note for Codespaces

Due to potential timing issues with Codespaces setup (`postStartCommand`), the background services (like the database) might not start automatically. After your Codespace has loaded, open a terminal and run:

```bash
docker compose up -d redis postgres
```

(Or simply `docker compose up -d` to ensure all services defined in the compose file are running). This ensures the necessary services are available before running the API.

## Changing Codespace Machine Type

If you find that the default Codespace machine type is too slow or you need more resources (CPU, RAM, Storage), you can change it:

*   **When creating a new Codespace:** Before clicking "Create codespace", click on the three dots (...) next to the button or the "Advanced options" link (the UI may vary slightly). This will allow you to select a more powerful machine type.
*   **For an existing Codespace:** You can change the machine type for an existing Codespace. Go to your list of Codespaces on GitHub (github.com/codespaces). Click the three dots (...) next to the Codespace you want to change, select "Change machine type", and choose a new one. The Codespace will then need to be reopened or rebuilt to apply the changes.

Using a more powerful machine type may incur higher costs if you are outside of the free tier for GitHub Codespaces.

For more general information, you can also refer to the official [GitHub Codespaces documentation](https://docs.github.com/en/codespaces).
