#!/bin/env python

import os
import json
from pathlib import Path
from shutil import which

if which("gp"):
    exit()

api_path = os.getcwd()

vscode_folder_path = Path(f"{api_path}/.vscode").resolve()
vscode_setting_path = Path(f"{api_path}/.vscode/settings.json").resolve()

if not os.path.isdir(vscode_folder_path):
    os.mkdir(vscode_folder_path)

vscode_setting_json = {}

if os.path.isfile(vscode_setting_path):
    # import yaml
    os.system(f"pipenv run python -m scripts.utils.fix_json {vscode_setting_path}")

    with open(vscode_setting_path, "r") as vscode_setting_file:
        vscode_setting_json = json.load(vscode_setting_file)

vscode_setting_json["python.languageServer"] = "Pylance"

bad_keys = [key for key in vscode_setting_json if key.startswith("//")]
for key in bad_keys:
    del vscode_setting_json[key]

with open(vscode_setting_path, "w") as vscode_setting_file:
    json.dump(vscode_setting_json, vscode_setting_file, indent=2)
