from collections import abc

import msgspec


class SpriteDto(msgspec.Struct, omit_defaults=True):
    gfx: str
    image: str
    # joint
    reloaded: bool = False


class GfxPackDto(msgspec.Struct):
    base_url: str
    sprites: abc.Sequence[SpriteDto]
