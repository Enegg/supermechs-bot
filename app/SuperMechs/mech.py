from __future__ import annotations

import typing as t
from collections import Counter
from functools import partial
from types import MappingProxyType
from uuid import UUID

from attrs import Attribute, define, field
from attrs.validators import max_len
from typing_extensions import Self

from shared.decorators import cached_slot_property
from typeshed import XOrTupleXY, dict_items_as

from .converters import get_slot_name, slot_to_type
from .core import STATS, WORKSHOP_STATS, ArenaBuffs, GameVars, StringLimits
from .enums import Element, Type
from .inv_item import InvItem
from .utils import format_count

__all__ = ("Mech",)

BODY_SLOTS = ("torso", "legs", "drone")
WEAPON_SLOTS = ("side1", "side2", "side3", "side4", "top1", "top2")
SPECIAL_SLOTS = ("tele", "charge", "hook")
MODULE_SLOTS = ("mod1", "mod2", "mod3", "mod4", "mod5", "mod6", "mod7", "mod8")

SlotType = InvItem | None
"""Nullable inventory item."""


def get_weight_emoji(vars: GameVars, weight: int) -> str:
    if weight < 0:
        return "🗿"
    if weight < vars.MAX_WEIGHT * 0.99:
        return "⚙️"
    if weight < vars.MAX_WEIGHT:
        return "🆗"
    if weight == vars.MAX_WEIGHT:
        return "👌"
    if weight <= vars.MAX_OVERWEIGHT:
        return "❕"
    return "⛔"


def get_weight_usage(mech: Mech, weight: int) -> str:
    return " " + get_weight_emoji(mech.game_vars, weight)


# ------------------------------------------ Constraints -------------------------------------------


def jumping_required(mech: Mech) -> bool:
    # unequipping legs is allowed, so no legs tests positive
    return mech.legs is None or "jumping" in mech.legs.stats


def no_duplicate_stats(mech: Mech, module: InvItem) -> bool:
    exclusive_stats = module.current_stats.keys() & mech.game_vars.EXCLUSIVE_STATS

    for equipped_module in mech.iter_items(modules=True):
        if equipped_module is None or equipped_module is module:
            continue

        if equipped_module.stats.has_any_of_stats(*exclusive_stats):
            return False

    return True


def get_constraints_of_item(item: InvItem, vars: GameVars) -> t.Callable[[Mech], bool] | None:
    if item.type is Type.MODULE and item.stats.has_any_of_stats(*vars.EXCLUSIVE_STATS):
        return partial(no_duplicate_stats, module=item)

    if item.tags.require_jump:
        return jumping_required

    return None


# ------------------------------------------- Validators -------------------------------------------


def _is_valid_type(
    inst: t.Any,
    attr: Attribute[InvItem | None | t.Any],
    value: InvItem | None | t.Any,
) -> None:
    """Performs a check if item assigned to a slot has valid type."""
    if value is None:
        return

    if not isinstance(value, InvItem):
        raise TypeError(f"Invalid object set as item: {type(value)}")

    valid_type = slot_to_type(attr.name)

    if value.type is not valid_type:
        raise ValueError(f"Mech slot {attr.name} expects a type {valid_type}, got {value.type}")


def assert_not_custom(mech: Mech) -> bool:
    for item in filter(None, mech.iter_items()):
        if item.tags.custom:
            return False

    return True


@define(kw_only=True)
class Mech:
    """Represents a mech build."""

    name: str = field(validator=max_len(StringLimits.name))
    custom: bool = False
    game_vars: GameVars = field(factory=GameVars.default)
    constraints: dict[UUID, t.Callable[[Self], bool]] = field(factory=dict, init=False)
    _stats: dict[str, int] = field(init=False, repr=False, eq=False)
    _dominant_element: Element | None = field(init=False, repr=False, eq=False)

    # fmt: off
    torso:  SlotType = field(default=None, validator=_is_valid_type)
    legs:   SlotType = field(default=None, validator=_is_valid_type)
    drone:  SlotType = field(default=None, validator=_is_valid_type)
    side1:  SlotType = field(default=None, validator=_is_valid_type)
    side2:  SlotType = field(default=None, validator=_is_valid_type)
    side3:  SlotType = field(default=None, validator=_is_valid_type)
    side4:  SlotType = field(default=None, validator=_is_valid_type)
    top1:   SlotType = field(default=None, validator=_is_valid_type)
    top2:   SlotType = field(default=None, validator=_is_valid_type)
    tele:   SlotType = field(default=None, validator=_is_valid_type)
    charge: SlotType = field(default=None, validator=_is_valid_type)
    hook:   SlotType = field(default=None, validator=_is_valid_type)
    mod1:   SlotType = field(default=None, validator=_is_valid_type)
    mod2:   SlotType = field(default=None, validator=_is_valid_type)
    mod3:   SlotType = field(default=None, validator=_is_valid_type)
    mod4:   SlotType = field(default=None, validator=_is_valid_type)
    mod5:   SlotType = field(default=None, validator=_is_valid_type)
    mod6:   SlotType = field(default=None, validator=_is_valid_type)
    mod7:   SlotType = field(default=None, validator=_is_valid_type)
    mod8:   SlotType = field(default=None, validator=_is_valid_type)
    # fmt: on

    def __setitem__(self, slot: XOrTupleXY[str | Type, int], item: SlotType, /) -> None:
        if not isinstance(item, (InvItem, type(None))):
            raise TypeError(f"Expected Item object or None, got {type(item)}")

        slot = get_slot_name(slot)

        if item is not None:
            if slot_to_type(slot) is not item.type:
                raise TypeError(f"Item type {item.type} does not match slot {slot!r}")

            if item.tags.custom and not self.custom:
                raise TypeError("Cannot set a custom item on this mech")

            if (prev := self[slot]) is not None and prev.UUID in self.constraints:
                del self.constraints[prev.UUID]

            if (constraint := get_constraints_of_item(item, self.game_vars)) is not None:
                self.constraints[item.UUID] = constraint

        del self.stats

        self.try_invalidate_cache(item, self[slot])
        setattr(self, slot, item)

    def __getitem__(self, slot: XOrTupleXY[str | Type, int]) -> SlotType:
        return getattr(self, get_slot_name(slot))

    def __str__(self) -> str:
        string_parts = [
            f"{item.type.name.capitalize()}: {item}"
            for item in self.iter_items(body=True)
            if item is not None
        ]

        if weapon_string := ", ".join(format_count(self.iter_items(weapons=True))):
            string_parts.append("Weapons: " + weapon_string)

        string_parts.extend(
            f"{item.type.name.capitalize()}: {item}"
            for item in self.iter_items(specials=True)
            if item is not None
        )

        if modules := ", ".join(format_count(self.iter_items(modules=True))):
            string_parts.append("Modules: " + modules)

        return "\n".join(string_parts)

    @property
    def weight(self) -> int:
        """The weight of the mech."""
        return self.stats.get("weight", 0)

    def validate(self) -> bool:
        """Check if the mech is battle ready."""
        return (
            # torso present
            self.torso is not None
            # legs present
            and self.legs is not None
            # at least one weapon
            and any(wep is not None for wep in self.iter_items(weapons=True))
            # not over max overload
            and self.weight <= self.game_vars.MAX_OVERWEIGHT
            # no constraints are broken
            and all(constr(self) for constr in self.constraints.values())
        )

    def check_integrity(self) -> None:
        """Go through items and validate that they are of correct type."""
        invalid_slots: list[str] = []

        for item, slot in self.iter_items(slots=True):
            if item is None:
                continue

            if slot_to_type(slot) is not item.type:
                invalid_slots.append(slot)

        if invalid_slots:
            raise ValueError(f"Slots: {', '.join(invalid_slots)} have invalid item type")

    @cached_slot_property
    def stats(self) -> t.Mapping[str, int]:
        """A dict of the mech's stats, in order as they appear in workshop."""

        # inherit the order of dict keys from workshop stats
        stats = dict.fromkeys(WORKSHOP_STATS, 0)

        for item in filter(None, self.iter_items()):
            for stat in stats:
                if (value := item.current_stats.get(stat)) is not None:
                    stats[stat] += value

        if (overweight := stats["weight"] - self.game_vars.MAX_WEIGHT) > 0:
            for stat, penalty_mult in dict_items_as(int, self.game_vars.PENALTIES):
                stats[stat] -= overweight * penalty_mult

        for stat, value in tuple(stats.items())[2:]:  # keep weight and health
            if value == 0:
                del stats[stat]

        return MappingProxyType(stats)

    def print_stats(
        self,
        included_buffs: ArenaBuffs | None = None,
        /,
        *,
        line_format: str = "{stat.emoji} **{value}** {stat.name}{extra}",
        extra: t.Mapping[str, t.Callable[[Mech, int], t.Any]] = {"weight": get_weight_usage},
    ) -> str:
        """Returns a string of lines formatted with mech stats.

        Parameters
        ----------
        included_buffs:
        `ArenaBuffs` object to apply the buffs from,
        or None if plain stats are desired.
        line_format: a string which will be used with `.format` to denote the format of each line.
        The keywords available are:
            - `stat` - a `Stat` object.
            - `value` - the integer value of the stat.
            - `extra` - any extra data coming from a callable from the `extra` param.
        """
        if included_buffs is None:
            bank = self.stats

        else:
            bank = included_buffs.buff_stats(self.stats, buff_health=True)

        def default_extra(mech: Mech, value: int) -> t.Any:
            return ""

        return "\n".join(
            line_format.format(
                value=value,
                stat=STATS[stat_name],
                extra=extra.get(stat_name, default_extra)(self, value),
            )
            for stat_name, value in bank.items()
        )

    def try_invalidate_cache(self, new: SlotType, old: SlotType) -> None:
        """Deletes cached attributes if they expire."""
        # # Setting a displayable item will not change the image
        # # only if the old item was the same item
        # # For simplicity I don't exclude that case from updating the image
        # if new is not None and new.type.displayable:
        #     del self.image

        # # the item was set to None, thus the appearance will change
        # # only if the previous one was displayable
        # elif old is not None and old.type.displayable:
        #     del self.image

        if new is None or old is None or new.element is not old.element:
            del self.dominant_element

    @t.overload
    def iter_items(
        self,
        *,
        body: bool = ...,
        weapons: bool = ...,
        specials: bool = ...,
        modules: bool = ...,
        slots: t.Literal[False] = False,
    ) -> t.Iterator[SlotType]:
        ...

    @t.overload
    def iter_items(
        self,
        *,
        body: bool = ...,
        weapons: bool = ...,
        specials: bool = ...,
        modules: bool = ...,
        slots: t.Literal[True],
    ) -> t.Iterator[tuple[SlotType, str]]:
        ...

    def iter_items(
        self,
        *,
        body: bool = False,
        weapons: bool = False,
        specials: bool = False,
        modules: bool = False,
        slots: bool = False,
    ) -> t.Iterator[XOrTupleXY[SlotType, str]]:
        """Iterator over mech's selected items.

        Parameters
        ----------
        body, weapons, specials, modules: `bool`
            Selectors denoting which groups of parts to yield.
            If none are set to `True`, yields from all groups.
            - `body` yields torso, legs and drone;
            - `weapons` yields side & top weapons;
            - `specials` yields teleport, charge and hook;
            - `modules` yields modules.

        slots: `bool`
            If `True`, yields all selected items as tuple pairs of (`InvItem`, `str`).
            If `False`, yields only the items.

        Yields
        ------
        `InvItem`
            If `slots` is set to `False`.
        `tuple[InvItem, str]`
            If `slots` is set to `True`.
        """

        if not (body or weapons or specials or modules):
            body = weapons = specials = modules = True

        from itertools import compress

        if slots:

            def factory(slot: str):
                return (getattr(self, slot), slot)

        else:
            factory = partial(getattr, self)

        for slot_group in compress(
            (BODY_SLOTS, WEAPON_SLOTS, SPECIAL_SLOTS, MODULE_SLOTS),
            (body, weapons, specials, modules),
        ):
            for slot in slot_group:
                yield factory(slot)

    @cached_slot_property
    def dominant_element(self) -> Element | None:
        """Guesses the mech type by equipped items."""
        excluded = {Type.CHARGE_ENGINE, Type.TELEPORTER}
        elements = Counter(
            item.element
            for item in self.iter_items(body=True, weapons=True, specials=True)
            if item is not None
            if item.type not in excluded
        ).most_common(2)

        # return None when there are no elements
        # or the difference between the two most common is small
        if len(elements) == 0 or (len(elements) >= 2 and elements[0][1] - elements[1][1] < 2):
            return None

        # otherwise just return the most common one
        return elements[0][0]
