import os

env = " ".join(
    [
        f'--env NEW_RELIC_APP_NAME={os.getenv("NEW_RELIC_APP_NAME")}',
        f'--env NEW_RELIC_LICENSE_KEY={os.getenv("NEW_RELIC_LICENSE_KEY")}',
        f'--env NEW_RELIC_LOG={os.getenv("NEW_RELIC_LOG")}',
        f'--env NEW_RELIC_API_KEY={os.getenv("NEW_RELIC_API_KEY")}',
        f'--env NEW_RELIC_ACCOUNT_ID={os.getenv("NEW_RELIC_ACCOUNT_ID")}',
    ]
)

os.system(f"podman build -t 4geeks . -f ./.heroku.Dockerfile {env}  ")
env = os.environ.copy()
