from __future__ import annotations

import math
import typing as t
from itertools import zip_longest

from disnake import ButtonStyle, Embed, MessageInteraction

from typeshed import dict_items_as, twotuple
from ui.action_row import ActionRow, MessageUIComponent
from ui.buttons import Button, ToggleButton, button
from ui.views import InteractionCheck, SaneView, positioned

from SuperMechs.core import MAX_BUFFS, STATS, Stat
from SuperMechs.item import AnyItem
from SuperMechs.typedefs import AnyStats


class ItemView(InteractionCheck, SaneView[ActionRow[MessageUIComponent]]):
    def __init__(
        self,
        embed: Embed,
        item: AnyItem,
        factory: t.Callable[[AnyItem, bool, bool], t.Iterable[tuple[str, str, bool]]],
        *,
        user_id: int,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.embed = embed
        self.item = item
        self.field_factory = factory

        if not item.stats.has_any_of_stats("phyDmg", "eleDmg", "expDmg"):
            self.remove_item(self.avg_button, 0)

        for name, value, inline in factory(item, False, False):
            embed.add_field(name, value, inline=inline)

    @positioned(0, 0)
    @button(cls=ToggleButton, label="Buffs", custom_id="button:buffs")
    async def buff_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        self.embed.clear_fields()
        for name, value, inline in self.field_factory(self.item, button.on, self.avg_button.on):
            self.embed.add_field(name, value, inline=inline)
        await inter.response.defer()
        await inter.edit_original_message(embed=self.embed, view=self)

    @positioned(0, 1)
    @button(cls=ToggleButton, label="Damage average", custom_id="button:dmg")
    async def avg_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        self.embed.clear_fields()
        for name, value, inline in self.field_factory(self.item, self.buff_button.on, button.on):
            self.embed.add_field(name, value, inline=inline)
        await inter.response.defer()
        await inter.edit_original_message(embed=self.embed, view=self)

    @positioned(0, 2)
    @button(label="Quit", style=ButtonStyle.red, custom_id="button:quit")
    async def quit_button(self, _: Button[None], inter: MessageInteraction) -> None:
        self.stop()
        await inter.response.defer()


class ItemCompareView(InteractionCheck, SaneView[ActionRow[MessageUIComponent]]):
    def __init__(
        self,
        embed: Embed,
        item_a: AnyItem,
        item_b: AnyItem,
        *,
        user_id: int,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.embed = embed
        self.item_a = item_a
        self.item_b = item_b

        self.update()

    @positioned(0, 0)
    @button(cls=ToggleButton, label="Arena buffs", custom_id="button:buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        self.update()
        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(0, 1)
    @button(label="Quit", style=ButtonStyle.red, custom_id="button:quit")
    async def quit_button(self, button: Button[None], inter: MessageInteraction) -> None:
        await inter.response.defer()
        self.stop()

    def update(self) -> None:
        items_stats = (self.item_a.max_stats, self.item_b.max_stats)

        if self.buffs_button.on:
            items_stats = map(MAX_BUFFS.buff_stats, items_stats)

        name_field, first_field, second_field = stats_to_fields(*items_stats)

        if require_jump := self.item_a.tags.require_jump:
            first_field.append("❕")

        if self.item_b.tags.require_jump:
            second_field.append("❕")
            require_jump = True

        if require_jump:
            name_field.append(f"{STATS['jump'].emoji} **Jumping required**")

        if self.embed._fields:
            modify_field_at = self.embed.set_field_at

        else:
            modify_field_at = self.embed.insert_field_at

        modify_field_at(0, "Stat", "\n".join(name_field))
        modify_field_at(1, try_shorten(self.item_a.name), "\n".join(first_field))
        modify_field_at(2, try_shorten(self.item_b.name), "\n".join(second_field))


def standard_deviation(*numbers: float) -> twotuple[float]:
    """Calculate the average and the standard deviation from a sequence of numbers."""
    if not numbers:
        raise ValueError("No arguments passed")

    avg = sum(numbers) / len(numbers)
    # √(∑(x-avg)² ÷ n)
    deviation = math.sqrt(sum((x - avg) ** 2 for x in numbers) / len(numbers))

    return avg, deviation


def buffed_stats(
    stats: AnyStats, buffs_enabled: bool
) -> t.Iterator[tuple[str, twotuple[tuple[int, ...]]]]:
    if buffs_enabled:
        apply_buff = MAX_BUFFS.buff_with_difference

    else:

        def apply_buff(_: str, value: int, /) -> twotuple[int]:
            return (value, 0)

    for stat, value in dict_items_as(int | list[int], stats):
        if stat == "health":
            assert type(value) is int
            yield stat, ((value,), (0,))
            continue

        match value:
            case int():
                value, diff = apply_buff(stat, value)
                yield stat, ((value,), (diff,))

            case [int() as x, y] if x == y:
                value, diff = apply_buff(stat, x)
                yield stat, ((value,), (diff,))

            case [x, y]:
                vx, dx = apply_buff(stat, x)
                vy, dy = apply_buff(stat, y)
                yield stat, ((vx, vy), (dx, dy))

            case _:
                raise TypeError(f"Unexpected value: {value}")


def truncate_float(num: float, digits: int) -> tuple[float, int]:
    num = round(num, digits)
    if num.is_integer():
        return num, 0
    return num, digits


def value_formatter(values: tuple[int, ...], prec: int = 1) -> str:
    return "-".join(map(str, values))


def diffs_formatter(diffs: tuple[int, ...], prec: int = 1) -> str:
    return "{0:+.{1}f}".format(*truncate_float(sum(diffs) / len(diffs), prec)) if diffs[0] else ""


def avg_value_formatter(values: tuple[int, ...], prec: int = 1) -> str:
    avg, dev = standard_deviation(*values)
    return "{0:.{1}f} ~{2:.{3}f}%".format(
        *truncate_float(avg, 1), *truncate_float(dev / avg * 100, prec)
    )


FormatterT = t.Callable[[tuple[int, ...]], str]
PrecFormatterT = t.Callable[[tuple[int, ...], int], str]
formatters: dict[str, tuple[FormatterT | None, FormatterT | None, PrecFormatterT | None]] = {
    "range": (None, lambda _: "", value_formatter),
}


def shared_iter(stats: AnyStats, buffs_enabled: bool, avg: bool, prec: int = 1) -> t.Iterator[tuple[str, str, str]]:
    for stat, (values, diffs) in buffed_stats(stats, buffs_enabled):
        val_fmt, diff_fmt, avg_fmt = formatters.get(stat, (None, None, None))

        val_fmt = val_fmt or value_formatter
        diff_fmt = diff_fmt or diffs_formatter
        avg_fmt = avg_fmt or avg_value_formatter

        if avg and len(values) > 1:
            str_value = avg_fmt(values, prec)

        else:
            str_value = val_fmt(values)

        change = diff_fmt(diffs)

        yield stat, str_value, change


def default_fields(item: AnyItem, buffs_enabled: bool, avg: bool) -> t.Iterator[tuple[str, str, bool]]:
    """Fills embed with full-featured info about an item."""
    yield ("Transform range: ", item.transform_range.as_tier_str(), False)

    spaced = False
    item_stats = ""  # the main string
    cost_stats = {"backfire", "heaCost", "eneCost"}

    for stat, str_value, change in shared_iter(item.max_stats, buffs_enabled, avg):
        if not spaced and stat in cost_stats:
            item_stats += "\n"
            spaced = True

        if change:
            change = f" **{change}**"

        name = STATS[stat].name

        if stat == "uses":
            name = "Use" if str_value == "1" else "Uses"

        item_stats += f"{STATS[stat].emoji} **{str_value}** {name}{change}\n"

    if item.tags.require_jump:
        item_stats += f"{STATS['jump'].emoji} **Jumping required**"

    yield ("Stats:", item_stats, False)


def compact_fields(item: AnyItem, buffs_enabled: bool, avg: bool) -> t.Iterator[tuple[str, str, bool]]:
    """Fills embed with reduced in size item info."""
    lines: list[str] = []

    for stat, str_value, _ in shared_iter(item.max_stats, buffs_enabled, avg, 0):
        lines.append(f"{STATS[stat].emoji} **{str_value}**")

    if item.tags.require_jump:
        lines.append(f"{STATS['jump'].emoji}❗")

    line_count = len(lines)
    div = wrap_nicely(line_count, 4)

    field_text = ("\n".join(lines[i : i + div]) for i in range(0, line_count, div))
    transform_range = item.transform_range.as_tier_str()

    for name, field in zip_longest((transform_range,), field_text, fillvalue="⠀"):
        yield (name, field, True)


def wrap_nicely(size: int, max: int) -> int:
    """Returns the size for a slice of a sequence of given size, distributed evenly according to max."""
    if size < max:
        return max
    for n in range(max, 2, -1):
        rem = size % n
        if rem == 0 or rem >= n - 1:
            return n
    return max


@t.overload
def cmp_num(x: int, y: int, lower_is_better: bool = ...) -> twotuple[twotuple[int]]:
    ...


@t.overload
def cmp_num(x: float, y: float, lower_is_better: bool = ...) -> twotuple[twotuple[float]]:
    ...


def cmp_num(x: float, y: float, lower_is_better: bool = False) -> twotuple[twotuple[float]]:
    if x == y:
        return ((x, 0), (y, 0))

    return ((x, x - y), (y, 0)) if lower_is_better ^ (x > y) else ((x, 0), (y, y - x))


@t.overload
def compare_numbers(x: int, y: int, lower_is_better: bool = ...) -> twotuple[int]:
    ...


@t.overload
def compare_numbers(x: float, y: float, lower_is_better: bool = ...) -> twotuple[int]:
    ...


def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    if x == y:
        return (0, 0)

    return (x - y, 0) if lower_is_better ^ (x > y) else (0, y - x)


value_and_diff = tuple[int | float | None, float]


def comparator(
    stats_a: AnyStats, stats_b: AnyStats
) -> t.Iterator[
    tuple[
        Stat,
        twotuple[value_and_diff]
        | tuple[value_and_diff, value_and_diff, value_and_diff, value_and_diff],
    ]
]:
    special_cases = {"range"}

    for stat_name, stat in STATS.items():
        stat_a: int | list[int] | None = stats_a.get(stat_name)
        stat_b: int | list[int] | None = stats_b.get(stat_name)

        if stat_name in special_cases and not (stat_a is stat_b is None):
            yield stat, (
                tuple(stat_a) if isinstance(stat_a, list) else (None, 0),
                tuple(stat_b) if isinstance(stat_b, list) else (None, 0),
            )
            continue

        match stat_a, stat_b:
            case (None, None):
                continue

            case (int() as a, int() as b):
                yield stat, cmp_num(a, b, not stat.beneficial)
                continue

            case ([int() as a1, int() as a2], [int() as b1, int() as b2]):
                x_avg, x_inacc = standard_deviation(a1, a2)
                y_avg, y_inacc = standard_deviation(b1, b2)

                yield stat, cmp_num(x_avg, y_avg, False) + cmp_num(
                    x_inacc, y_inacc, True
                )
                continue

            case _:
                pass

        if isinstance(stat_a, int):
            yield stat, ((stat_a, 0), (None, 0))

        elif isinstance(stat_b, int):
            yield stat, ((None, 0), (stat_b, 0))

        elif stat_a is not None:
            avg, inacc = standard_deviation(*stat_a)
            yield stat, ((avg, 0), (None, 0), (inacc, 0), (None, 0))

        elif stat_b is not None:
            avg, inacc = standard_deviation(*stat_b)
            yield stat, ((None, 0), (avg, 0), (None, 0), (inacc, 0))


def stats_to_fields(stats_a: AnyStats, stats_b: AnyStats) -> tuple[list[str], list[str], list[str]]:
    name_field: list[str] = []
    first_item: list[str] = []
    second_item: list[str] = []

    for stat, long_boy in comparator(stats_a, stats_b):
        name_field.append(f"{stat.emoji} {stat.name}")

        match stat.key, long_boy:
            case "range", ((a1, a2), (b1, b2)):
                first_item.append(f"**{a1}-{a2}**" if a1 is not None else "")
                second_item.append(f"**{b1}-{b2}**" if b1 is not None else "")

            case _, ((_, _), (_, _)) as tup:
                for (value, diff), field in zip(tup, (first_item, second_item)):
                    if value is None:
                        string = ""

                    elif diff == 0:
                        string = f"**{value:g}**"

                    else:
                        string = f"**{value:g}** {diff:+g}"

                    field.append(string)

            case _, ((_, _), (_, _), (_, _), (_, _)) as tup:
                name_field.append("🎲 Damage spread")

                for (avg, diff), (spread, s_diff), field in zip(
                    tup[:2], tup[2:], (first_item, second_item)
                ):
                    if avg is None:
                        string = ""

                    elif diff == 0:
                        string = f"**{avg:g}**"

                    else:
                        string = f"**{avg:g}** {diff:+g}"

                    field.append(string)

                    if spread is None:
                        string = ""

                    elif s_diff == 0:
                        string = f"**{spread:.1%}**"

                    else:
                        string = f"**{spread:.1%}** {s_diff:+.1%}"

                    field.append(string)

            case _:
                raise ValueError("Invalid structure")

    return name_field, first_item, second_item


def try_shorten(name: str) -> str:
    if len(name) < 16:
        return name

    return "".join(s for s in name if s.isupper())