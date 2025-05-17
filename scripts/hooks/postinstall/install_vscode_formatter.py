#!/bin/env python

import json
import os
import subprocess
from pathlib import Path

api_path = os.getcwd()

vscode_folder_path = Path(f"{api_path}/.vscode").resolve()
vscode_setting_path = Path(f"{api_path}/.vscode/settings.json").resolve()

if not os.path.isdir(vscode_folder_path):
    os.mkdir(vscode_folder_path)

vscode_setting_json = {}

if os.path.isfile(vscode_setting_path):
    # import yaml
    os.system(f"poetry run python -m scripts.utils.fix_json {vscode_setting_path}")

    with open(vscode_setting_path, "r") as vscode_setting_file:
        vscode_setting_json = json.load(vscode_setting_file)


if "python.formatting.provider" in vscode_setting_json:
    del vscode_setting_json["python.formatting.provider"]

vscode_setting_json["[python]"] = {}
vscode_setting_json["[python]"]["editor.formatOnSaveMode"] = "file"
vscode_setting_json["[python]"]["editor.formatOnSave"] = True
vscode_setting_json["[python]"]["editor.defaultFormatter"] = "ms-python.black-formatter"
vscode_setting_json["[python]"]["editor.codeActionsOnSave"] = {}
vscode_setting_json["[python]"]["editor.codeActionsOnSave"]["source.organizeImports"] = "explicit"
vscode_setting_json["isort.args"] = [
    "--profile",
    "black",
]

python_path = subprocess.run(
    ["poetry", "run", "which", "python"], capture_output=True, text=True, check=True
).stdout.strip()

vscode_setting_json["python.defaultInterpreterPath"] = python_path
vscode_setting_json["aws.telemetry"] = False


bad_keys = [key for key in vscode_setting_json if key.startswith("//")]
for key in bad_keys:
    del vscode_setting_json[key]

with open(vscode_setting_path, "w") as vscode_setting_file:
    json.dump(vscode_setting_json, vscode_setting_file, indent=2)
