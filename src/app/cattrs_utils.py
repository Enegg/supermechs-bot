from typing import Any, Final, NewType

import cattrs

from discord.emoji import AnyEmoji, CustomEmoji, UnicodeEmoji
from disnake import Color, PartialEmoji

from app.utils import atoi_bin
from resources import AnyResource, from_uri

ByteSize = NewType("ByteSize", int)

CONVERTER: Final = cattrs.Converter()


@CONVERTER.register_structure_hook
def _structure_color(value: int, cls: type) -> Color:
    return Color(int(value))


def _structure_resource(value: str, cls: type) -> AnyResource:
    assert isinstance(value, str)
    return from_uri(value)


CONVERTER.register_structure_hook_func(lambda x: x is AnyResource, _structure_resource)


def _structure_emoji(value: str, cls: type) -> AnyEmoji:
    partial_emoji = PartialEmoji.from_str(value)
    if partial_emoji.id is None:
        return UnicodeEmoji(partial_emoji.name)
    return CustomEmoji(partial_emoji.id, partial_emoji.name, partial_emoji.animated)


CONVERTER.register_structure_hook_func(lambda x: x is AnyEmoji, _structure_emoji)


@CONVERTER.register_structure_hook
def _structure_binary_int(value: Any, _: object) -> ByteSize:
    try:
        return ByteSize(int(value))

    except (ValueError, TypeError):
        pass

    if not isinstance(value, str):
        msg = f"Invalid type: {value!r}"
        raise TypeError(msg) from None

    return ByteSize(atoi_bin(value))


del _structure_color, _structure_resource, _structure_binary_int
