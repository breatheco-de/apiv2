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

### If something goes wrong

execute this to get a diagnosis.

```bash
python -m scripts.doctor
```
