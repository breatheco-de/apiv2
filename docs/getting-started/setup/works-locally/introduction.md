# Introduction

You should choose to work locally if your machine is faster than the machine of [Gitpod](https://www.gitpod.io) and [Codespaces](https://github.com/features/codespaces), otherwise, I would recommend you work on the [cloud](https://en.wikipedia.org/wiki/Cloud_computing).

## Set up 4geeks dependencies

### Option one: install Docker (Required for Devcontainer)

Install [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/), if you use Linux you can know what your Linux distribution running `uname -n`.

#### Why install Docker and Docker Composer

4geeks depends on [Postgres](https://www.postgresql.org/download/) and [Redis](https://redis.io) to open the server, the easier way to set up these dependencies for the development team is using a configuration file, it is that Docker does.

#### Can I use Podman and Podman Compose?

Podman supports Dockerfile and Docker Compose files, you should install [Podman](https://podman.io)

#### Must I install Docker Engine/Podman or Docker Desktop/Podman Desktop?

Windows users and Mac users usually install Docker Desktop, and Linux users install Docker Engine, my recommendation is if you use Windows, install Docker Desktop because it is complicated to install on Windows, in Mac and Linux choose Docker Desktop if you want to manage it with and graphical interface, else install Docker Engine.

#### Can I use Podman to run Devcontainer?

Yes, but you should have compatibility issues.

### Option two: install Postgres and Redis manually

Read, install, and configure [Postgres](https://www.postgresql.org/download/) and [Redis](https://redis.io).

### Advantages of working locally.

- It offers less latency than using an editor on the cloud.
- May provide better performance than works in the cloud if your machine is older.
- It will work even without the internet.

### Disadvantages of using an Editor on the Cloud.

- May provide better performance than works in the cloud if your machine is older.
- You will deal with the configurations.
