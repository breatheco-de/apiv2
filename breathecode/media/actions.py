from typing import Literal


class Emit:
    """This class was defined to emit events to the frontend."""

    def __init__(self, level: Literal["INFO", "WARNING", "ERROR"], message: str):
        self.level = level
        self.message = message

    @classmethod
    def info(cls, message: str) -> "Emit":
        return cls("INFO", message)

    @classmethod
    def warning(cls, message: str) -> "Emit":
        return cls("WARNING", message)

    @classmethod
    def error(cls, message: str) -> "Emit":
        return cls("ERROR", message)
