from __future__ import annotations
from abc import ABC
from faker import Faker

from .garbage_collector import GarbageCollector
from .cache import Cache
from .datetime import Datetime
# from .request import Request
from .database import Database
from .check import Check
from .format import Format
from .random import Random


class BreathecodeInterface(ABC):

    cache: Cache
    random: Random
    datetime: Datetime
    # request: Request
    database: Database
    check: Check
    format: Format
    fake: Faker
    garbage_collector: GarbageCollector
