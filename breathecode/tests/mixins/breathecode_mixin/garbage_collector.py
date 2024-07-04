from __future__ import annotations
from io import TextIOWrapper
import os
from rest_framework.test import APITestCase
from faker import Faker
from . import interfaces

__all__ = ["Check"]
fake = Faker()

IMAGE_TYPES = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
}


class GarbageCollector:
    """Mixin with the purpose of cover all the related with the custom asserts"""

    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface
    _files: list[TextIOWrapper]

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc
        self._files = []

    def collect(self):
        """
        Collect the garbage.

        Usage:

        ```py
        self.bc.garbage_collector.collect()
        ```
        """
        for file in self._files:
            os.remove(file.name)

    def register_file(self, file: TextIOWrapper) -> None:
        """
        Register a file to be collected.

        Usage:

        ```py
        with open('aaa.txt', 'r') as f:
            self.bc.garbage_collector.register_file(f)
        ```
        """

        self._files.append(file)

    def register_image(self, file: TextIOWrapper) -> None:
        """
        Register a image to be collected.

        Usage:

        ```py
        with open('aaa.txt', 'r') as f:
            self.bc.garbage_collector.register_image(f)
        ```
        """

        self.register_file(file)
