from collections import abc

import msgspec

from app.dto.common import MixedJointsDto, Point2DDto
from app.models.joints import Joints
from app.models.sprite_pack import SpriteKey
from vec2 import Point2D

type JointsMapping = abc.Mapping[SpriteKey, Joints]


def convert_point_2d(in_: Point2DDto | msgspec.UnsetType, /) -> Point2D:
    if in_ is msgspec.UNSET:
        return Point2D.ZERO

    return Point2D(x=in_.x, y=in_.y)


def convert_joints(in_: MixedJointsDto, /) -> Joints:
    match in_.x, in_.y:
        case (int() as x, int() as y):
            torso = Point2D(x=x, y=y)

        case _:
            torso = Point2D.ZERO

    return Joints(
        torso=torso,
        leg_1=convert_point_2d(in_.leg1),
        leg_2=convert_point_2d(in_.leg2),
        side_weapon_1=convert_point_2d(in_.side1),
        side_weapon_2=convert_point_2d(in_.side2),
        side_weapon_3=convert_point_2d(in_.side3),
        side_weapon_4=convert_point_2d(in_.side4),
        top_weapon_1=convert_point_2d(in_.top1),
        top_weapon_2=convert_point_2d(in_.top2),
    )
