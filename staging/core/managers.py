import os
from typing import Optional

from dotenv import dotenv_values


class EnvLoader:
    def __init_subclass__(cls) -> None:
        cls._load_flags()

    @classmethod
    def _load_flags(cls) -> None:
        values = dotenv_values(".env.flags")
        for key, value in values.items():
            os.environ[f"FLAGS_{key}"] = value


class FlagEnv:
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        if not key.startswith("FLAGS_"):
            key = f"FLAGS_{key}"

        return os.environ.get(key, default)

    @classmethod
    def set(cls, key: str, value: str) -> None:
        if not key.startswith("FLAGS_"):
            key = f"FLAGS_{key}"

        os.environ[key] = value

    @classmethod
    def delete(cls, key: str) -> None:
        if not key.startswith("FLAGS_"):
            key = f"FLAGS_{key}"

        del os.environ[key]

    @classmethod
    def set_default(cls, key: str, value: str) -> None:
        if not key.startswith("FLAGS_"):
            key = f"FLAGS_{key}"

        os.environ.setdefault(key, value)
