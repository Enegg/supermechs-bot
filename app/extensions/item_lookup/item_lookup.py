import io
import typing as t
from itertools import zip_longest

from disnake import ButtonStyle, Embed, Locale, MessageInteraction
from disnake.ui import Button, button

import i18n
from assets import STAT, range_to_str
from library_extensions import SPACE, debug_footer
from library_extensions.ui import (
    ActionRow,
    MessageUIComponent,
    SaneView,
    ToggleButton,
    invoker_bound,
    positioned,
)
from typeshed import dict_items_as, twotuple

from .helpers import truncate_float, try_shorten, wrap_nicely

from supermechs.api import MAX_BUFFS, STATS, AnyStatsMapping, ItemData, Stat, ValueRange
from supermechs.ext.comparators.helpers import mean_and_deviation
from supermechs.item_stats import max_stats
from supermechs.utils import has_any_of


@invoker_bound
class ItemView(SaneView[ActionRow[MessageUIComponent]]):
    def __init__(
        self,
        embed: Embed,
        item: ItemData,
        factory: t.Callable[[ItemData, bool, bool, Locale], t.Iterable[tuple[str, str, bool]]],
        locale: Locale,
        *,
        user_id: int,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.embed = embed
        self.item = item
        self.field_factory = factory
        self.locale = locale

        if not has_any_of(item.start_stage.base_stats, "phyDmg", "eleDmg", "expDmg"):
            self.remove_item(self.avg_button, 0)

        for name, value, inline in factory(item, False, False, locale):
            embed.add_field(name, value, inline=inline)

    async def update(self, inter: MessageInteraction, buffs: bool, avg: bool) -> None:
        self.embed.clear_fields()
        for name, value, inline in self.field_factory(self.item, buffs, avg, self.locale):
            self.embed.add_field(name, value, inline=inline)

        if __debug__:
            debug_footer(self.embed)
        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(0, 0)
    @button(ToggleButton, label="Buffs")
    async def buff_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        await self.update(inter, button.on, self.avg_button.on)

    @positioned(0, 1)
    @button(ToggleButton, label="Damage average")
    async def avg_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        await self.update(inter, self.buff_button.on, button.on)

    @positioned(0, 2)
    @button(label="Quit", style=ButtonStyle.red)
    async def quit_button(self, _: Button[None], inter: MessageInteraction) -> None:
        self.stop()
        await inter.response.defer()


@invoker_bound
class ItemCompareView(SaneView[ActionRow[MessageUIComponent]]):
    def __init__(
        self,
        embed: Embed,
        item_a: ItemData,
        item_b: ItemData,
        locale: Locale,
        *,
        user_id: int,
        timeout: float = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.embed = embed
        self.item_a = item_a
        self.item_b = item_b
        self.locale = locale

        self.update()

    @positioned(0, 0)
    @button(ToggleButton, label="Arena buffs")
    async def buffs_button(self, button: ToggleButton, inter: MessageInteraction) -> None:
        button.toggle()
        self.update()
        await inter.response.edit_message(embed=self.embed, view=self)

    @positioned(0, 1)
    @button(label="Quit", style=ButtonStyle.red)
    async def quit_button(self, _: Button[None], inter: MessageInteraction) -> None:
        await inter.response.defer()
        self.stop()

    def update(self) -> None:
        items_stats = (max_stats(self.item_a.start_stage), max_stats(self.item_b.start_stage))

        if self.buffs_button.on:
            items_stats = map(MAX_BUFFS.buff_stats, items_stats)

        name_field, first_field, second_field = stats_to_fields(*items_stats)

        if require_jump := self.item_a.tags.require_jump:
            first_field.append("❕")

        if self.item_b.tags.require_jump:
            second_field.append("❕")
            require_jump = True

        if require_jump:
            emoji = STAT["jump"]
            name_field.append(f"{emoji} **Jumping required**")

        if self.embed._fields:
            modify_field_at = self.embed.set_field_at

        else:
            modify_field_at = self.embed.insert_field_at

        modify_field_at(0, "Stat", "\n".join(name_field).format_map(i18n.get_entries(self.locale)))
        modify_field_at(1, try_shorten(self.item_a.name), "\n".join(first_field))
        modify_field_at(2, try_shorten(self.item_b.name), "\n".join(second_field))

        if __debug__:
            debug_footer(self.embed)


def buffed_stats(
    stats: AnyStatsMapping, buffs_enabled: bool
) -> t.Iterator[tuple[str, twotuple[tuple[int, ...]]]]:
    if buffs_enabled:
        apply_buff = MAX_BUFFS.buff_with_difference

    else:

        def apply_buff(_: str, value: int, /) -> twotuple[int]:
            return (value, 0)

    for stat, value in dict_items_as(int | ValueRange, stats):
        if stat == "health":
            assert isinstance(value, int)
            yield stat, ((value,), (0,))
            continue

        match value:
            case int():
                value, diff = apply_buff(stat, value)
                yield stat, ((value,), (diff,))

            case ValueRange(x, y) if x == y:
                value, diff = apply_buff(stat, x)
                yield stat, ((value,), (diff,))

            case ValueRange(x, y):
                vx, dx = apply_buff(stat, x)
                vy, dy = apply_buff(stat, y)
                yield stat, ((vx, vy), (dx, dy))

            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise TypeError(f"Unexpected value: {value}")


def value_formatter(values: tuple[int, ...], prec: int = 1) -> str:
    return "-".join(map(str, values))


def diffs_formatter(diffs: tuple[int, ...], prec: int = 1) -> str:
    return "{0:+.{1}f}".format(*truncate_float(sum(diffs) / len(diffs), prec)) if diffs[0] else ""


def avg_value_formatter(values: tuple[int, ...], prec: int = 1) -> str:
    avg, dev = mean_and_deviation(*values)
    return "{0:.{1}f} ~{2:.{3}f}%".format(
        *truncate_float(avg, 1), *truncate_float(dev / avg * 100, prec)
    )


def shared_iter(
    stats: AnyStatsMapping, buffs_enabled: bool, avg: bool, prec: int = 1
) -> t.Iterator[tuple[str, str, str]]:
    for stat_key, (values, diffs) in buffed_stats(stats, buffs_enabled):
        if stat_key == "range":
            avg_fmt = value_formatter
            change = ""

        else:
            avg_fmt = avg_value_formatter
            change = diffs_formatter(diffs)

        str_value = avg_fmt(values, prec) if avg and len(values) > 1 else value_formatter(values)

        yield stat_key, str_value, change


def default_fields(
    item: ItemData, buffs_enabled: bool, avg: bool, locale: Locale
) -> t.Iterator[tuple[str, str, bool]]:
    """Fills embed with full-featured info about an item."""
    yield ("Transform range: ", range_to_str(item.transform_range), False)

    spaced = False
    string_builder = io.StringIO()
    cost_stats = {"backfire", "heaCost", "eneCost"}

    for stat_key, str_value, change in shared_iter(max_stats(item.start_stage), buffs_enabled, avg):
        if not spaced and stat_key in cost_stats:
            string_builder.write("\n")
            spaced = True

        if change:
            change = f" **{change}**"

        string_builder.write(
            f"{STAT[stat_key]} **{str_value}** {i18n.get(locale, stat_key)}{change}\n"
        )

    if item.tags.require_jump:
        emoji = STAT["jump"]
        string_builder.write(f"{emoji} **Jumping required**")

    yield ("Stats:", string_builder.getvalue(), False)


def compact_fields(
    item: ItemData, buffs_enabled: bool, avg: bool, *_
) -> t.Iterator[tuple[str, str, bool]]:
    """Fills embed with reduced in size item info."""
    lines: list[str] = []

    for stat_key, str_value, _ in shared_iter(max_stats(item.start_stage), buffs_enabled, avg, 0):
        lines.append(f"{STAT[stat_key]} **{str_value}**")

    if item.tags.require_jump:
        lines.append(f"{STAT['jump']}❗")

    line_count = len(lines)
    div = wrap_nicely(line_count, 4)

    field_text = ("\n".join(lines[i : i + div]) for i in range(0, line_count, div))
    transform_range = range_to_str(item.transform_range)

    for name, field in zip_longest((transform_range,), field_text, fillvalue=SPACE):
        yield (name, field, True)


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


value_and_diff = tuple[int | float | None, float]


def comparator(
    stats_a: AnyStatsMapping, stats_b: AnyStatsMapping
) -> t.Iterator[
    tuple[
        Stat,
        twotuple[value_and_diff]
        | tuple[value_and_diff, value_and_diff, value_and_diff, value_and_diff],
    ]
]:
    for stat_key, stat in STATS.items():
        stat_a: int | ValueRange | None = stats_a.get(stat_key)
        stat_b: int | ValueRange | None = stats_b.get(stat_key)

        if stat_key == "range" and stat_a is not None and stat_b is not None:
            yield stat, (
                stat_a if isinstance(stat_a, ValueRange) else (None, 0),
                stat_b if isinstance(stat_b, ValueRange) else (None, 0),
            )
            continue

        match stat_a, stat_b:
            case (None, None):
                continue

            case (int() as a, int() as b):
                yield stat, cmp_num(a, b, not stat.beneficial)
                continue

            case ([int() as a1, int() as a2], [int() as b1, int() as b2]):
                x_avg, x_inacc = mean_and_deviation(a1, a2)
                y_avg, y_inacc = mean_and_deviation(b1, b2)
                x_inacc /= x_avg
                y_inacc /= y_avg

                yield stat, cmp_num(x_avg, y_avg, False) + cmp_num(x_inacc, y_inacc, True)
                continue

            case _:
                pass

        if isinstance(stat_a, int):
            yield stat, ((stat_a, 0), (None, 0))

        elif isinstance(stat_b, int):
            yield stat, ((None, 0), (stat_b, 0))

        elif stat_a is not None:
            avg, inacc = mean_and_deviation(*stat_a)
            inacc /= avg
            yield stat, ((avg, 0), (None, 0), (inacc, 0), (None, 0))

        elif stat_b is not None:
            avg, inacc = mean_and_deviation(*stat_b)
            inacc /= avg
            yield stat, ((None, 0), (avg, 0), (None, 0), (inacc, 0))


def stats_to_fields(
    stats_a: AnyStatsMapping, stats_b: AnyStatsMapping
) -> tuple[list[str], list[str], list[str]]:
    name_field: list[str] = []
    first_item: list[str] = []
    second_item: list[str] = []

    for stat, long_boy in comparator(stats_a, stats_b):
        name_field.append(f"{STAT[stat.key]} {{{stat.key}}}")

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
                        string = f"**{spread * 100:.1f}%**"

                    else:
                        string = f"**{spread * 100:.1f}%** {s_diff * 100:+.1f}%"

                    field.append(string)

            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError("Invalid structure")

    return name_field, first_item, second_item
