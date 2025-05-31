from typing import Generic, Protocol, TypeVar

import attrs

from dupermechs.enums import MechSlot

__all__ = ("IMech", "Mech")

T = TypeVar("T", covariant=True)


class IMech[ItemT](Protocol):
    @property
    def torso(self) -> ItemT | None: ...
    @property
    def legs(self) -> ItemT | None: ...
    @property
    def drone(self) -> ItemT | None: ...
    @property
    def side_weapon_1(self) -> ItemT | None: ...
    @property
    def side_weapon_2(self) -> ItemT | None: ...
    @property
    def side_weapon_3(self) -> ItemT | None: ...
    @property
    def side_weapon_4(self) -> ItemT | None: ...
    @property
    def top_weapon_1(self) -> ItemT | None: ...
    @property
    def top_weapon_2(self) -> ItemT | None: ...
    @property
    def charge(self) -> ItemT | None: ...
    @property
    def teleport(self) -> ItemT | None: ...
    @property
    def hook(self) -> ItemT | None: ...
    @property
    def shield(self) -> ItemT | None: ...
    @property
    def perk(self) -> ItemT | None: ...
    @property
    def module_1(self) -> ItemT | None: ...
    @property
    def module_2(self) -> ItemT | None: ...
    @property
    def module_3(self) -> ItemT | None: ...
    @property
    def module_4(self) -> ItemT | None: ...
    @property
    def module_5(self) -> ItemT | None: ...
    @property
    def module_6(self) -> ItemT | None: ...
    @property
    def module_7(self) -> ItemT | None: ...
    @property
    def module_8(self) -> ItemT | None: ...

    def __getitem__(self, slot: MechSlot, /) -> ItemT | None: ...


@attrs.frozen(kw_only=True)
class Mech(Generic[T]):
    Slot = MechSlot

    torso: T | None = None
    legs: T | None = None
    drone: T | None = None
    side_weapon_1: T | None = None
    side_weapon_2: T | None = None
    side_weapon_3: T | None = None
    side_weapon_4: T | None = None
    top_weapon_1: T | None = None
    top_weapon_2: T | None = None
    charge: T | None = None
    teleport: T | None = None
    hook: T | None = None
    shield: T | None = None
    perk: T | None = None
    module_1: T | None = None
    module_2: T | None = None
    module_3: T | None = None
    module_4: T | None = None
    module_5: T | None = None
    module_6: T | None = None
    module_7: T | None = None
    module_8: T | None = None

    def __getitem__(self, slot: Slot, /) -> T | None:
        return getattr(self, slot.name)
