import yaml
import os
from yaml.loader import FullLoader

CONFIGURATION_FILE = os.path.join(os.getcwd(), ".breathecode.yml")
NEW_ENVS = []


def reset_environment():
    system_environment = set(os.environ)

    with open(CONFIGURATION_FILE, "r") as file:
        configuration = yaml.load(file, Loader=FullLoader)
        whitelist_environment = set(configuration["tests"]["environments"]["whitelist"])

    blacklist_environment = system_environment.difference(whitelist_environment)

    for env in blacklist_environment:
        if env in os.environ:
            del os.environ[env]


def test_environment():
    os.environ["ENV"] = "test"


def celery_worker_environment():
    os.environ["CELERY_WORKER_RUNNING"] = "True"
