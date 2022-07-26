from io import TextIOWrapper
import os
import random
import string
from rest_framework.test import APITestCase
from faker import Faker
import numpy as np
from PIL import Image
from faker import Faker
import tempfile

__all__ = ['Check']
fake = Faker()


class Random:
    """Mixin with the purpose of cover all the related with the custom asserts"""

    _parent: APITestCase

    def __init__(self, parent) -> None:
        self._parent = parent

    def image(self, width: int = 10, height: int = 10) -> tuple[TextIOWrapper, str]:
        """
        Generate a random image.

        Usage:

        ```py
        # generate a random image with width of 20px and height of 10px
        file, filename = self.bc.random.image(20, 10)
        ```
        """

        size = (width, height)
        filename = fake.slug() + '.png'
        image = Image.new('RGB', size)
        arr = np.random.randint(low=0, high=255, size=(size[1], size[0]))

        image = Image.fromarray(arr.astype('uint8'))
        image.save(filename, 'PNG')

        file = open(filename, 'rb')

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

        file = tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False)
        file.write(os.urandom(1024))

        return file, file.name

    def string(self, lower=False, upper=False, symbol=False, number=False, size=0) -> str:
        chars = ''

        if lower:
            chars = chars + string.ascii_lowercase

        if upper:
            chars = chars + string.ascii_uppercase

        if symbol:
            chars = chars + string.punctuation

        if number:
            chars = chars + string.digits

        return ''.join(random.choices(chars, k=size))
