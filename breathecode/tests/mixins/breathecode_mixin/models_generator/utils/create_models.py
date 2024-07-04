from typing import Any

from breathecode.tests.mixins.generate_models_mixin.exceptions import BadArgument
from mixer.backend.django import mixer

from .argument_parser import argument_parser

__all__ = ["create_models"]

list_of_args = list[tuple[int, dict[str, Any]]]
args = list[tuple[int, dict[str, Any]]]


def cycle(how_many):
    return mixer.cycle(how_many) if how_many > 1 else mixer


def create_models(attr, path, **kwargs):
    result = [
        cycle(how_many).blend(
            path,
            **{
                **kwargs,
                **arguments,
            }
        )
        for how_many, arguments in argument_parser(attr)
    ]

    if len(result) == 1:
        result = result[0]

    return result
