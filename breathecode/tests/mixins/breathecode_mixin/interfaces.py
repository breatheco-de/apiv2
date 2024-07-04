from __future__ import annotations

from abc import ABC

from faker import Faker

from .cache import Cache
from .check import Check
from .database import Database
from .datetime import Datetime
from .format import Format
from .garbage_collector import GarbageCollector
from .random import Random
from .request import Request


class BreathecodeInterface(ABC):

    cache: Cache
    random: Random
    datetime: Datetime
    request: Request
    database: Database
    check: Check
    format: Format
    fake: Faker
    garbage_collector: GarbageCollector
