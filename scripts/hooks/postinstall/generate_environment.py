import os
from pathlib import Path

from shutil import which, copyfile

api_path = os.getcwd()
env_path = Path(f"{api_path}/.env").resolve()
env_example_path = Path(f"{api_path}/.env.example").resolve()
where_in_docker = os.getenv("DOCKER") == "1"

if which("gp"):
    copyfile(env_example_path, env_path)
    exit()

content = ""
with open(env_example_path, "r") as file:
    lines = file.read().split("\n")

for line in lines:
    try:
        key, value = line.split("=")

        if key == "DATABASE_URL":
            hostname = "postgres" if where_in_docker else "localhost"
            content += f"{key}=postgres://user:pass@{hostname}:5432/breathecode\n"

        elif key == "REDIS_URL":
            hostname = "redis" if where_in_docker else "localhost"
            content += f"{key}=redis://{hostname}:6379\n"

        elif key == "API_URL":
            content += f"{key}=http://localhost:8000\n"

        else:
            content += f"{key}={value}\n"

    except Exception:
        content += "\n"

with open(env_path, "w") as file:
    file.write(content)
