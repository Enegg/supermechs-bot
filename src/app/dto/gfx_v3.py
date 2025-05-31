from collections import abc

import msgspec

from .common import Point2DDto


class JointDto(msgspec.Struct):
    torso: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    leg1: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    leg2: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    side1: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    side2: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    side3: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    side4: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    top1: Point2DDto | msgspec.UnsetType = msgspec.UNSET
    top2: Point2DDto | msgspec.UnsetType = msgspec.UNSET


class SpriteDto(msgspec.Struct, omit_defaults=True):
    gfx: str
    image: str
    reloaded: bool = False
    joint: JointDto | msgspec.UnsetType = msgspec.UNSET


class GfxPackDto(msgspec.Struct):
    base_url: str
    sprites: abc.Sequence[SpriteDto]
