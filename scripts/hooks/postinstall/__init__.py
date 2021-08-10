from os.path import dirname, isfile, join
import glob

modules = glob.glob(join(dirname(__file__), '*.py'))
scripts = [f for f in modules if isfile(f) and not f.endswith('__init__.py')]
__all__ = ['scripts']
