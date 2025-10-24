import logging
import os

import yaml
from yaml.loader import FullLoader

logger = logging.getLogger(__name__)

CONFIGURATION_FILE = os.path.join(os.getcwd(), ".breathecode.yml")
NEW_ENVS = []

with open(CONFIGURATION_FILE, "r") as file:
    data = yaml.load(file, Loader=FullLoader) or {}

if "tests" not in data:
    data["tests"] = {}

if "environments" not in data["tests"]:
    data["tests"]["environments"] = {}

if "whitelist" not in data["tests"]["environments"]:
    data["tests"]["environments"]["whitelist"] = []

whitelist_environment = set(data["tests"]["environments"]["whitelist"])
system_environment = set(os.environ)

whitelist_environment.update(system_environment)

data["tests"]["environments"]["whitelist"] = list(whitelist_environment)

with open(CONFIGURATION_FILE, "w") as file:
    yaml.dump(data, file, indent=2)
