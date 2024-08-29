import os
from typing import Generator, final

import numpy as np
import pytest
from faker import Faker
from PIL import Image as PilImage

__all__ = ["image", "Image"]


@final
class Image:
    """
    Image utils.
    """

    def __init__(self, fake: Faker) -> None:
        self._fake = fake
        self._filenames = []

    def random(self, x_size: int, y_size: int):
        """
        Generate a random image.

        Parameters:
        - x_size (int): A int representing the size in X axis.
        - y_size (int): A int representing the size in Y axis.

        Returns:
        - file (bytes): A binary file object containing the generated random image.

        Usage:

        ```python
        file = image.random(100, 100)
        ```

        The function generates a random image of the specified size and returns a binary file object containing the image data.
        """

        size = (y_size, x_size)

        filename = self._fake.slug() + ".png"
        while filename in self._filenames:
            filename = self._fake.slug() + ".png"

        image = PilImage.new("RGB", size)
        arr = np.random.randint(low=0, high=255, size=(size[1], size[0]))

        image = PilImage.fromarray(arr.astype("uint8"))
        image.save(filename, "PNG")

        file = open(filename, "rb")
        self._filenames.append(filename)

        return file

    def _teardown(self):
        for filename in self._filenames:
            os.remove(filename)


@pytest.fixture()
def image(fake) -> Generator[Image, None, None]:
    """Image fixtures."""

    x = Image(fake)

    yield x

    x._teardown()
