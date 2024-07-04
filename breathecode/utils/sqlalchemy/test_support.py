import os
import sys
import inspect

__all__ = ["test_support"]


def test_support(module):
    if os.getenv("ENV") != "test":
        return

    from .big_query import BigQueryBase

    for x in dir(sys.modules[module]):
        if "__" in x:
            continue

        loaded_module = getattr(sys.modules[module], x, None)

        if not loaded_module:
            continue

        if not inspect.isclass(loaded_module):
            continue

        if not issubclass(loaded_module, BigQueryBase):
            continue

        loaded_module.__name__ = loaded_module.__name__.replace(".", "__")
