import subprocess
from shutil import which

__all__ = ["get_python_path"]


def get_python_path_per_executable(python3=False):
    python_path = which("python" + "3" if python3 else "")

    if not python_path:
        return

    result = subprocess.run([python_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout.decode("utf-8").startswith("Python 3"):
        return python_path


def get_python_path():
    path = get_python_path_per_executable()
    if path:
        return path

    path = get_python_path_per_executable(python3=True)
    if path:
        return path

    raise Exception("Python 3 is not installed")
