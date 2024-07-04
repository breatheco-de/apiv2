import yaml
import sys
import json

from yaml.loader import FullLoader

if len(sys.argv) < 2:
    exit()

with open(sys.argv[1], "r") as file:
    data = yaml.load(file, Loader=FullLoader)

with open(sys.argv[1], "w") as file:
    json.dump(data, file, indent=2)
