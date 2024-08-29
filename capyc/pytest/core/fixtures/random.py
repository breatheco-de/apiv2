import random as r
import string
from typing import Any, Dict, Generator, Optional, Tuple, final

import pytest
from faker import Faker

__all__ = ["random", "Random"]


@final
class Random:
    """
    Random utils.
    """

    def __init__(self, fake: Faker, seed: Optional[int]) -> None:
        self._fake = fake
        r.seed(seed)

    def seed(self, a=None, version=2) -> None:
        """Initialize internal state from a seed.

        The only supported seed types are None, int, float,
        str, bytes, and bytearray.

        None or no argument seeds from current time or from an operating
        system specific randomness source if available.

        If *a* is an int, all bits are used.

        For version 2 (the default), all of the bits are used if *a* is a str,
        bytes, or bytearray.  For version 1 (provided for reproducing random
        sequences from older versions of Python), the algorithm for str and
        bytes generates a narrower range of seeds.
        """

        r.seed(a=a, version=version)

    def tuple(self, *args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        """Generate a random tuple."""

        return self._fake.pytuple(*args, **kwargs)

    def dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Generate a random dict."""

        return self._fake.pydict(*args, **kwargs)

    def args(self, *args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        """Generate a random tuple."""

        return self.tuple(*args, **kwargs)

    def kwargs(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Generate a random dict."""

        return self.dict(*args, **kwargs)

    def int(self, min: int = 0, max: int = 1000) -> int:
        """
        Generate a random integer within a specified range.

        Parameters:
        - min (int): The minimum value of the range. Default is 0.
        - max (int): The maximum value of the range. Default is 1000.

        Returns:
        - int: A random integer within the specified range.

        This method uses the built-in `random.randint()` function to generate a random integer between the given `min` and `max` values.
        """

        return r.randint(min, max)

    def string(self, size=0, lower=False, upper=False, symbol=False, number=False) -> str:
        """
        Generate a random string of specified size and optional character types.

        Parameters:
        - size (int): The desired length of the generated string. Default is 0.
        - lower (bool): If True, include lowercase letters in the generated string. Default is False.
        - upper (bool): If True, include uppercase letters in the generated string. Default is False.
        - symbol (bool): If True, include punctuation symbols in the generated string. Default is False.
        - number (bool): If True, include digits in the generated string. Default is False.

        Returns:
        - str: A random string of the specified size and character types.
        """

        chars = ""

        if lower:
            chars += string.ascii_lowercase

        if upper:
            chars += string.ascii_uppercase

        if symbol:
            chars += string.punctuation

        if number:
            chars += string.digits

        return "".join(r.choices(chars, k=size))


@pytest.fixture(autouse=True)
def random(fake: Faker, seed: Optional[int]) -> Generator[Random, None, None]:
    """Image fixtures."""

    x = Random(fake, seed)

    yield x
