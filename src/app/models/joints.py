from typing import ClassVar, Protocol, Self

import attrs

from vec2 import Point2D


@attrs.frozen(kw_only=True)
class Joints:
    ZERO: ClassVar[Self]

    hat: Point2D = Point2D.ZERO
    torso: Point2D = Point2D.ZERO
    leg_1: Point2D = Point2D.ZERO
    leg_2: Point2D = Point2D.ZERO
    jump_jet: Point2D = Point2D.ZERO
    side_weapon_1: Point2D = Point2D.ZERO
    side_weapon_2: Point2D = Point2D.ZERO
    side_weapon_3: Point2D = Point2D.ZERO
    side_weapon_4: Point2D = Point2D.ZERO
    top_weapon_1: Point2D = Point2D.ZERO
    top_weapon_2: Point2D = Point2D.ZERO


Joints.ZERO = Joints()


class IJoints(Protocol):
    @property
    def hat(self) -> Point2D: ...
    @property
    def torso(self) -> Point2D: ...
    @property
    def leg_1(self) -> Point2D: ...
    @property
    def leg_2(self) -> Point2D: ...
    @property
    def side_weapon_1(self) -> Point2D: ...
    @property
    def side_weapon_2(self) -> Point2D: ...
    @property
    def side_weapon_3(self) -> Point2D: ...
    @property
    def side_weapon_4(self) -> Point2D: ...
    @property
    def top_weapon_1(self) -> Point2D: ...
    @property
    def top_weapon_2(self) -> Point2D: ...
