import subprocess
from shutil import which

__all__ = ["get_pip_path"]


def get_pip_path_per_executable(pip3=False):
    pip_path = which("pip" + "3" if pip3 else "")

    if not pip_path:
        return

    result = subprocess.run([pip_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout.decode("utf-8").find("pip (python 3"):
        return pip_path


def get_pip_path():
    path = get_pip_path_per_executable()
    if path:
        return path

    path = get_pip_path_per_executable(pip3=True)
    if path:
        return path

    raise Exception("Python 3 is not installed")
