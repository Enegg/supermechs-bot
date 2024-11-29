from collections import abc
from typing import Any

from cattrs import gen

from app.models.graphics import Joints
from smparse.converter import converter
from smparse.gfx.models import AnyGfx, ItemGfx, ItemPackGfx, SpritesSheetGfx
from vec2 import Point2D

converter.register_structure_hook(
    ItemGfx,
    gen.make_dict_structure_fn(
        ItemGfx,
        converter,
        joints=gen.override(rename="attachment"),
    ),
)
converter.register_structure_hook(
    SpritesSheetGfx,
    gen.make_dict_structure_fn(
        SpritesSheetGfx,
        converter,
        sprites_url=gen.override(rename="spritesSheet"),
        sprites_map=gen.override(rename="spritesMap"),
    ),
)
_joint_hook = gen.make_dict_structure_fn(
    Joints,
    converter,
    leg_1=gen.override(rename="leg1"),
    leg_2=gen.override(rename="leg2"),
    side_weapon_1=gen.override(rename="side1"),
    side_weapon_2=gen.override(rename="side2"),
    side_weapon_3=gen.override(rename="side3"),
    side_weapon_4=gen.override(rename="side4"),
    top_weapon_1=gen.override(rename="top1"),
    top_weapon_2=gen.override(rename="top2"),
)


@converter.register_structure_hook
def joint_converter(obj: abc.Mapping[str, Any], _: type) -> Joints:
    if "x" in obj or "y" in obj:
        return Joints(torso=converter.structure(obj, Point2D))

    return _joint_hook(obj, Joints)


def structure_gfx(data: abc.Mapping[str, Any], /) -> AnyGfx:
    version = str(data.get("version", "1"))

    known_formats = {
        "1": ItemPackGfx,
        "2": SpritesSheetGfx,
        "3": SpritesSheetGfx,
    }
    format = known_formats.get(version)

    if format is None:
        raise NotImplementedError(version)

    return converter.structure(data, format)
