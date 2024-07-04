from __future__ import annotations

import os
import random
import string
import tempfile
from io import TextIOWrapper

import numpy as np
from faker import Faker
from PIL import Image
from rest_framework.test import APITestCase

from . import interfaces

__all__ = ["Random", "fake"]
fake = Faker()

IMAGE_TYPES = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
}


class Random:
    """Mixin with the purpose of cover all the related with the custom asserts"""

    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc

    def image(self, width: int = 10, height: int = 10, ext="png") -> tuple[TextIOWrapper, str]:
        """
        Generate a random image.

        Usage:

        ```py
        # generate a random image with width of 20px and height of 10px
        file, filename = self.bc.random.image(20, 10)
        ```
        """

        size = (width, height)
        filename = fake.slug() + f".{ext}"
        image = Image.new("RGB", size)
        arr = np.random.randint(low=0, high=255, size=(size[1], size[0]))

        image = Image.fromarray(arr.astype("uint8"))
        image.save(filename, IMAGE_TYPES[ext])

        file = open(filename, "rb")

        self._bc.garbage_collector.register_image(file)

        return file, filename

    def file(self) -> tuple[TextIOWrapper, str]:
        """
        Generate a random file.

        Usage:

        ```py
        # generate a random file
        file, filename = self.bc.random.file()
        ```
        """

        ext = self.string(lower=True, size=2)

        file = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        file.write(os.urandom(1024))

        self._bc.garbage_collector.register_file(file)

        return file, file.name

    def string(self, lower=False, upper=False, symbol=False, number=False, size=0) -> str:
        chars = ""

        if lower:
            chars = chars + string.ascii_lowercase

        if upper:
            chars = chars + string.ascii_uppercase

        if symbol:
            chars = chars + string.punctuation

        if number:
            chars = chars + string.digits

        return "".join(random.choices(chars, k=size))
