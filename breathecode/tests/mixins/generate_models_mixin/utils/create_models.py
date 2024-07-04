import logging
from typing import Any

from mixer.backend.django import mixer

from breathecode.tests.mixins.generate_models_mixin.exceptions import BadArgument

from .argument_parser import argument_parser

__all__ = ["create_models"]

logger = logging.getLogger(__name__)

list_of_args = list[tuple[int, dict[str, Any]]]
args = list[tuple[int, dict[str, Any]]]


def cycle(how_many):
    return mixer.cycle(how_many) if how_many > 1 else mixer


def debug_mixer(attr, path, **kwargs):
    for how_many, arguments in argument_parser(attr):
        sentence = ""
        if how_many > 1:
            sentence += f"mixer.cycle({how_many}).blend("
        else:
            sentence += "mixer.blend("

        sentence += f"'{path}', "
        values = {
            **kwargs,
            **arguments,
        }
        for key in values:
            if isinstance(values[key], str):
                sentence += f"{key}='{values[key]}', "
            elif isinstance(values[key], int) or isinstance(values[key], list):
                sentence += f"{key}={values[key]}, "
            else:
                sentence += f"{key}=<{values[key]}>, "

        sentence = sentence[:-2] + ")"
        print(sentence)


def create_models(attr, path, **kwargs):
    # does not remove this line is used very often
    # debug_mixer(attr, path, **kwargs)

    result = [
        cycle(how_many).blend(
            path,
            **{
                **kwargs,
                **arguments,
            },
        )
        for how_many, arguments in argument_parser(attr)
    ]

    if len(result) == 1:
        result = result[0]

    return result
