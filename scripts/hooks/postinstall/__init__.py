from os.path import dirname, isfile, join, relpath
from os import getcwd
import glob

modules = glob.glob(join(dirname(__file__), "*.py"))
scripts = [
    relpath(f, getcwd()).replace("\\", ".").replace("/", ".").replace(".py", "")
    for f in modules
    if isfile(f) and not f.endswith("__init__.py")
]

__all__ = ["scripts"]
