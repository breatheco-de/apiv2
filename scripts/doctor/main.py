import json
import os
import sys
from pathlib import Path

from shutil import which
import socket

__all__ = ["main"]

api_path = os.getcwd()
dependencies_path = Path(f"{api_path}/scripts/doctor/dependencies.json").resolve()


def status(condition, true="yes", false="no"):
    return true if condition else false


def check_dependencies(dependencies):
    print("--- Check installation status ---\n")

    is_python_outdated = sys.version_info[0] < 3 or sys.version_info[1] < 9
    print("python =>", status(not is_python_outdated, "updated", "outdated"))
    for dependency in dependencies:
        print(f"{dependency} =>", status(which(dependency), "installed", "not installed"))


def port_is_open(host, port=80):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((host, port))
        if result == 0:
            return True
        else:
            return False


def check_conections():
    print("\n--- Check conection status ---\n")

    import subprocess

    result = subprocess.run(["docker", "image", "ls"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("docker =>", status(not result.stderr, "up", "down"))
    print("postgres =>", status(port_is_open("localhost", 5432), "up", "down"))
    print("redis =>", status(port_is_open("localhost", 6379), "up", "down"))


def main():
    with open(dependencies_path, "r") as file:
        dependencies = json.load(file)

    check_dependencies(dependencies)
    check_conections()
