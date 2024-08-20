import inspect
import logging
from typing import Any, Callable, Literal, Optional, Tuple, TypedDict, overload

logger = logging.getLogger(__name__)
__all__ = ["feature"]


type FeatureType = Literal["availability", "variant"]


class Meta(TypedDict):
    frontend: bool
    default: bool
    name: str
    type: FeatureType


class Feature:
    _flags: dict[FeatureType, dict[str, Tuple[Callable[..., str | bool], list[str], Meta]]] = {
        "availability": {},
        "variant": {},
    }
    TRUE = ["true", "TRUE", "True", "1", "on", "ON"]
    FALSE = ["false", "FALSE", "False", "0", "off", "OFF"]

    @classmethod
    def parameters(cls, fn: Callable) -> list[str]:
        signature = inspect.signature(fn)
        return [
            name
            for name, param in signature.parameters.items()
            if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and param.default is inspect.Parameter.empty
        ]

    @classmethod
    def availability(cls, name: str, frontend=True, default: Optional[bool] = None) -> bool:

        def decorator(fn: Callable[..., bool]) -> Callable[..., bool]:
            meta = {"frontend": frontend, "default": default, "name": name, "type": "availability"}
            return fn, meta

        return decorator

    @classmethod
    def variant(cls, name: str, frontend=True, default: Optional[str] = None) -> str:

        def decorator(fn: Callable[..., str]) -> Callable[..., str]:
            meta = {"frontend": frontend, "default": default, "name": name, "type": "variant"}
            return fn, meta

        return decorator

    @classmethod
    def is_enabled(cls, name: str, context: Optional[dict[str, Any]] = None, default: Optional[bool] = None) -> bool:
        return cls._get("availability", name, context, default)

    @classmethod
    def get_variant(cls, name: str, context: Optional[dict[str, Any]] = None, default: Optional[str] = None) -> str:
        return cls._get("variant", name, context, default)

    @classmethod
    def add(cls, *features: Tuple[Callable[..., str | bool], Meta]) -> None:
        for fn, meta in features:
            if callable(fn) is False:
                logger.error(f"Expected a callable, got {type(fn).__name__}")
                return

            params = cls.parameters(fn)
            cls._flags[meta["type"]][meta["name"]] = (fn, params, meta)

    @classmethod
    def context(cls, **context: Any) -> dict[str, Any]:
        return context

    @overload
    @classmethod
    def _get(
        cls, type: Literal["availability"], name: str, context: Optional[dict[str, Any]] = None, default: bool = False
    ) -> bool: ...

    @overload
    @classmethod
    def _get(
        cls, type: Literal["variant"], name: str, context: Optional[dict[str, Any]] = None, default: str = "unknown"
    ) -> str: ...

    @classmethod
    def _get(
        cls,
        type: FeatureType,
        name: str,
        context: Optional[dict[str, Any]] = None,
        default: Optional[str | bool] = None,
    ) -> str | bool:
        if context is None:
            context = {}

        info = cls._flags[type].get(name)
        if info:
            extra = {}
            fn, params, meta = info
            for param in params:
                if param not in context:
                    logger.debug(f"Missing required parameter '{param}', using None as default")
                    extra[param] = None

            try:
                value = fn(**context, **extra)
                if value is None:
                    v = False if type == "availability" else "unknown"
                    if default is not None:
                        v = default

                    elif meta["default"] is not None:
                        v = meta["default"]

                    return v

                return value

            except Exception:
                logger.exception(f"Error executing flag '{name}', using default value")
                return default

        logger.error(f"Flag '{name}' not found, using default value")
        return default

    @classmethod
    def namespace(cls, namespace: str) -> list[str]:
        return [flag for flag in cls._flags.keys() if flag.startswith(namespace)]

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._flags.keys())


feature = Feature()
