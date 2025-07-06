import io
from collections import abc
from typing import NamedTuple

from app.disnake_types import CommandInteraction
from discord import ComponentLimits, MessageLimits
from disnake import Embed, Event, Locale
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, EMOJIS, get_slot_icon
from app.commands.autocompleters import item_name_autocomplete
from app.commands.params import ELEMENT_CHOICES, TIER_CHOICES, TYPE_CHOICES
from app.core import CONFIG
from app.devtools import debug_message
from app.embed_utils import sikrit_footer
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from app.plugins_factory import create_plugin
from defer import Defer
from resources import HttpResource

from .helpers import (
    format_damage_average,
    format_damage_default,
    format_range,
    has_damage,
    has_damage_spread,
    item_transform_range,
)

import dupermechs.all as sm
from dupermechs import stats
from dupermechs.enums import ItemStat

plugin = create_plugin(__name__)


class ItemLookupUIContext(NamedTuple):
    item_id: sm.Item.Id
    stage_index: int
    level_index: int
    levels_page: int
    legacy: bool = False
    damage_average: bool = False
    buffs_enabled: bool = False
    damage_vs_titan: bool = False


class ComponentIds:
    __slots__ = ()

    stage_select = "stages"
    level_select = "levels"
    buffs_button = "buffs"
    avg_button = "avg"
    titan_button = "dvt"


@plugin.slash_command()
async def item(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
    legacy: bool = False,
) -> None:
    """Lookup item stats. {{ ITEM }}

    Parameters
    ----------
    name:
        The name of the item. {{ ITEM_NAME }}
    type:
        Limit suggestions to this type. {{ ITEM_TYPE }}
    element:
        Limit suggestions to this element. {{ ITEM_ELEMENT }}
    rarity:
        Remove suggestions below this rarity. {{ ITEM_TIER }}
    legacy:
        Show legacy items. {{ ITEM_LEGACY }}
    """  # noqa: D400
    for item in packs.filter_items(type, element, rarity, legacy):
        if item.name == name:
            break

    else:
        msg = i18n.get_message(i18n.get_locale(inter), "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    stage_index = len(item.stages) - 1
    levels = item.stages[stage_index].levels
    ctx = ItemLookupUIContext(
        item_id=item.id,
        stage_index=stage_index,
        level_index=0 if legacy else len(levels) - 1,
        levels_page=ui.PaginatedSelect.option_to_page_count(len(levels)),
        legacy=legacy,
    )
    embed, layout = get_item_summary(i18n.get_locale(inter), item, ctx)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)


def get_item(ctx: ItemLookupUIContext, /) -> sm.IItem:
    item_pack = packs.get_item_pack()
    bank = item_pack.legacy_items if ctx.legacy else item_pack.reloaded_items
    return bank[ctx.item_id]


def get_item_stats(item: sm.IItem, ctx: ItemLookupUIContext, /) -> sm.IItemStats:
    base_stats = item.stages[ctx.stage_index].levels[ctx.level_index].stats

    if not (ctx.buffs_enabled or ctx.damage_vs_titan):
        return base_stats

    total = [base_stats]

    if ctx.buffs_enabled:
        total.append(stats.bonus_item_stats(base_stats, MAXED_ARENA_BUFFS))

    if ctx.damage_vs_titan:
        total.append(stats.bonus_damage_vs_titan(base_stats, MAXED_ARENA_BUFFS))

    return stats.combine(total)


def make_component_id(
    component: str,
    ctx: ItemLookupUIContext,
) -> str:
    flags = ctx.damage_average | ctx.buffs_enabled << 1 | ctx.damage_vs_titan << 2 | ctx.legacy << 3
    return f"item-lookup:{component}:{ctx.item_id:x}:{ctx.stage_index}:{ctx.level_index}:{ctx.levels_page}:{flags:x}"


def parse_component_id(id: str, /) -> tuple[str, ItemLookupUIContext]:
    _, component, item_id, stage_index, level_index, levels_page, flags = id.split(":", 6)
    flags = int(flags, 16)
    return (
        component,
        ItemLookupUIContext(
            item_id=sm.Item.Id(int(item_id, 16)),
            stage_index=int(stage_index),
            level_index=int(level_index),
            levels_page=int(levels_page),
            damage_average=flags & 1 == 1,
            buffs_enabled=flags >> 1 & 1 == 1,
            damage_vs_titan=flags >> 2 & 1 == 1,
            legacy=flags >> 3 & 1 == 1,
        ),
    )


def make_level_options(
    locale: Locale,
    levels: abc.Iterable[sm.IStageLevel],
    selected_level_index: int,
    start: int = 0,
) -> list[ui.SelectOption]:
    return [
        ui.SelectOption(
            label=f"{i18n.get_message(locale, 'item-lookup-ui-level-select-label')} {level.level}",
            value=f"{n}",
            default=n == selected_level_index,
        )
        for n, level in enumerate(levels, start=start)
    ]


def make_option_up(locale: Locale, /) -> ui.SelectOption:
    return ui.SelectOption(
        label=i18n.get_message(locale, "item-lookup-ui-select-up-label"), value="$u", emoji="🔺"
    )


def make_option_down(locale: Locale, /) -> ui.SelectOption:
    return ui.SelectOption(
        label=i18n.get_message(locale, "item-lookup-ui-select-down-label"), value="$d", emoji="🔻"
    )


def get_item_summary(
    locale: Locale, item: sm.IItem, ctx: ItemLookupUIContext
) -> tuple[Embed, ui.MessageComponents]:
    gettext = i18n.get_gettext(locale)
    stage = item.stages[ctx.stage_index]
    levels = stage.levels
    name_parts: list[str] = []

    if item.element is not sm.Item.Element.other:
        name_parts.append(item.element.name)

    name_parts.append(item.type.name.replace("_", " "))
    name_parts[0] = name_parts[0].capitalize()

    if ctx.stage_index == len(item.stages) - 1 and ctx.level_index == len(levels) - 1:
        power_level = "max"

    else:
        power_level = str(levels[ctx.level_index].level)

    desc_lines: list[str] = [
        " ".join(name_parts),
        item_transform_range(item, ctx.stage_index),
        f"{gettext('item-lookup-power-level')}: **{power_level}**",
    ]
    item_stats = get_item_stats(item, ctx)
    stats_lines = format_stats(
        item_stats, locale, format_damage_average if ctx.damage_average else format_damage_default
    )
    if not stats_lines:
        desc_lines.append(f"-# {gettext('item-lookup-no-stats')}")

    sprite_url = gfx.get_image_url((item.id, stage.tier))

    match get_slot_icon(item.type):
        case HttpResource(url):
            icon_url = str(url)

        case _:
            icon_url = None

    embed = (
        Embed(
            title=item.name,
            description="\n".join(desc_lines),
            color=COLORS.elements[item.element],
        )
        .set_thumbnail(icon_url)
        .set_image(sprite_url)
    )
    if sprite_url is None:
        embed.set_footer(text=gettext("item-lookup-no-image"))
    if stats_lines:
        embed.add_field(
            f"{gettext('item-lookup-stats-header')}:", "\n".join(stats_lines), inline=False
        )

    layout: ui.MessageComponents = []

    if len(item.stages) > 1:
        stage_options = [
            ui.SelectOption(
                label=gettext(f"tier-{stage.tier.name}").capitalize(),  # noqa: INT001
                value=f"{i:x}",
                emoji=EMOJIS.tiers[stage.tier],
            )
            for i, stage in enumerate(item.stages)
        ]
        stage_options[ctx.stage_index].default = True
        layout.append([ui.StringSelect(
            options=stage_options,
            custom_id=make_component_id(ComponentIds.stage_select, ctx),
        )])  # fmt: skip

    total_pages = ui.PaginatedSelect.option_to_page_count(len(levels))

    if total_pages <= 1:
        level_options = make_level_options(locale, levels, ctx.level_index)

    elif ctx.levels_page == 1:
        level_options = make_level_options(
            locale, levels[: ComponentLimits.select_options - 1], ctx.level_index
        )
        level_options.append(make_option_down(locale))

    elif ctx.levels_page == total_pages:
        level_options = [make_option_up(locale)]
        offset = (ComponentLimits.select_options - 2) * (ctx.levels_page - 1) + 1
        level_options += make_level_options(locale, levels[offset:], ctx.level_index, offset)

    else:
        size = ComponentLimits.select_options - 2
        offset = size * (ctx.levels_page - 1) + 1
        level_options = [make_option_up(locale)]
        level_options += make_level_options(
            locale, levels[offset : offset + size], ctx.level_index, offset
        )
        level_options.append(make_option_down(locale))

    layout.append([ui.StringSelect(
        options=level_options,
        placeholder=gettext("item-lookup-ui-select-placeholder"),
        custom_id=make_component_id(ComponentIds.level_select, ctx),
    )])  # fmt: skip
    button_row: list[ui.ActionButton] = [ui.ActionButton(
        label=gettext("item-lookup-ui-buffs"),
        style=ui.ButtonStyle.green if ctx.buffs_enabled else ui.ButtonStyle.gray,
        custom_id=make_component_id(ComponentIds.buffs_button, ctx),
    )]  # fmt: skip
    layout.append(button_row)

    if has_damage_spread(item_stats):
        button_row.append(
            ui.ActionButton(
                label=gettext("item-lookup-ui-damage-avg"),
                style=ui.ButtonStyle.green if ctx.damage_average else ui.ButtonStyle.gray,
                custom_id=make_component_id(ComponentIds.avg_button, ctx),
            )
        )

    if has_damage(item_stats):
        button_row.append(
            ui.ActionButton(
                label=gettext("item-lookup-ui-damage-vs-titans"),
                style=ui.ButtonStyle.green if ctx.damage_vs_titan else ui.ButtonStyle.gray,
                custom_id=make_component_id(ComponentIds.titan_button, ctx),
            )
        )

    return embed, layout


def format_stats(
    item_stats: sm.IItemStats, locale: Locale, format_damage: abc.Callable[[int, int], str]
) -> list[str]:
    def fmt(emoji: str, value: int | str, stat_key: ItemStat, /) -> str:
        return f"{emoji} **{value}** {i18n.get_stat_name(locale, stat_key)}"

    stats_lines: list[str] = []
    emojis = EMOJIS.stats

    if item_stats.weight:
        stats_lines.append(fmt(emojis.weight, item_stats.weight, ItemStat.weight))
    if item_stats.hit_points:
        stats_lines.append(fmt(emojis.hit_points, item_stats.hit_points, ItemStat.hit_points))
    if item_stats.energy_capacity:
        stats_lines.append(
            fmt(emojis.energy_capacity, item_stats.energy_capacity, ItemStat.energy_capacity)
        )
    if item_stats.energy_regeneration:
        stats_lines.append(
            fmt(
                emojis.energy_regeneration,
                item_stats.energy_regeneration,
                ItemStat.energy_regeneration,
            )
        )
    if item_stats.heat_capacity:
        stats_lines.append(
            fmt(emojis.heat_capacity, item_stats.heat_capacity, ItemStat.heat_capacity)
        )
    if item_stats.heat_cooling:
        stats_lines.append(fmt(emojis.heat_cooling, item_stats.heat_cooling, ItemStat.heat_cooling))
    if item_stats.physical_resistance:
        stats_lines.append(
            fmt(
                emojis.physical_resistance,
                item_stats.physical_resistance,
                ItemStat.physical_resistance,
            )
        )
    if item_stats.explosive_resistance:
        stats_lines.append(
            fmt(
                emojis.explosive_resistance,
                item_stats.explosive_resistance,
                ItemStat.explosive_resistance,
            )
        )
    if item_stats.electric_resistance:
        stats_lines.append(
            fmt(
                emojis.electric_resistance,
                item_stats.electric_resistance,
                ItemStat.electric_resistance,
            )
        )
    if item_stats.bullets_capacity:
        stats_lines.append(
            fmt(
                emojis.bullets_capacity,
                item_stats.bullets_capacity,
                ItemStat.bullets_capacity,
            )
        )
    if item_stats.rockets_capacity:
        stats_lines.append(
            fmt(
                emojis.rockets_capacity,
                item_stats.rockets_capacity,
                ItemStat.rockets_capacity,
            )
        )
    if item_stats.physical_damage:
        stats_lines.append(
            fmt(
                emojis.physical_damage,
                format_damage(item_stats.physical_damage, item_stats.physical_damage_addon),
                ItemStat.physical_damage,
            )
        )
    if item_stats.physical_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.physical_resistance_damage,
                item_stats.physical_resistance_damage,
                ItemStat.physical_resistance_damage,
            )
        )
    if item_stats.electric_damage:
        stats_lines.append(
            fmt(
                emojis.electric_damage,
                format_damage(item_stats.electric_damage, item_stats.electric_damage_addon),
                ItemStat.electric_damage,
            )
        )
    if item_stats.energy_damage:
        stats_lines.append(
            fmt(emojis.energy_damage, item_stats.energy_damage, ItemStat.energy_damage)
        )
    if item_stats.energy_capacity_damage:
        stats_lines.append(
            fmt(
                emojis.energy_capacity_damage,
                item_stats.energy_capacity_damage,
                ItemStat.energy_capacity_damage,
            )
        )
    if item_stats.regeneration_damage:
        stats_lines.append(
            fmt(
                emojis.regeneration_damage,
                item_stats.regeneration_damage,
                ItemStat.regeneration_damage,
            )
        )
    if item_stats.electric_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.electric_resistance_damage,
                item_stats.electric_resistance_damage,
                ItemStat.electric_resistance_damage,
            )
        )
    if item_stats.explosive_damage:
        stats_lines.append(
            fmt(
                emojis.explosive_damage,
                format_damage(item_stats.explosive_damage, item_stats.explosive_damage_addon),
                ItemStat.explosive_damage,
            )
        )
    if item_stats.heat_damage:
        stats_lines.append(fmt(emojis.heat_damage, item_stats.heat_damage, ItemStat.heat_damage))
    if item_stats.heat_capacity_damage:
        stats_lines.append(
            fmt(
                emojis.heat_capacity_damage,
                item_stats.heat_capacity_damage,
                ItemStat.heat_capacity_damage,
            )
        )
    if item_stats.cooling_damage:
        stats_lines.append(
            fmt(emojis.cooling_damage, item_stats.cooling_damage, ItemStat.cooling_damage)
        )
    if item_stats.explosive_resistance_damage:
        stats_lines.append(
            fmt(
                emojis.explosive_resistance_damage,
                item_stats.explosive_resistance_damage,
                ItemStat.explosive_resistance_damage,
            )
        )
    if item_stats.walk:
        stats_lines.append(fmt(emojis.walk, item_stats.walk, ItemStat.walk))
    if item_stats.jump:
        stats_lines.append(fmt(emojis.jump, item_stats.jump, ItemStat.jump))
    if item_stats.range:
        stats_lines.append(
            fmt(
                emojis.range,
                format_range(item_stats.range, item_stats.range_addon),
                ItemStat.range,
            )
        )
    if item_stats.push:
        stats_lines.append(fmt(emojis.push, item_stats.push, ItemStat.push))
    if item_stats.pull:
        stats_lines.append(fmt(emojis.pull, item_stats.pull, ItemStat.pull))
    if item_stats.recoil:
        stats_lines.append(fmt(emojis.recoil, item_stats.recoil, ItemStat.recoil))
    if item_stats.advance:
        stats_lines.append(fmt(emojis.advance, item_stats.advance, ItemStat.advance))
    if item_stats.retreat:
        stats_lines.append(fmt(emojis.retreat, item_stats.retreat, ItemStat.retreat))
    if item_stats.uses:
        stats_lines.append(fmt(emojis.uses, item_stats.uses, ItemStat.uses))
    if item_stats.repair:
        stats_lines.append(fmt(emojis.repair, item_stats.repair, ItemStat.repair))
    if stats_lines:
        stats_lines.append("")
    if item_stats.backfire:
        stats_lines.append(fmt(emojis.backfire, item_stats.backfire, ItemStat.backfire))
    if item_stats.heat_generation:
        stats_lines.append(
            fmt(emojis.heat_generation, item_stats.heat_generation, ItemStat.heat_generation)
        )
    if item_stats.energy_cost:
        stats_lines.append(fmt(emojis.energy_cost, item_stats.energy_cost, ItemStat.energy_cost))
    if item_stats.bullets_cost:
        stats_lines.append(fmt(emojis.bullets_cost, item_stats.bullets_cost, ItemStat.bullets_cost))
    if item_stats.rockets_cost:
        stats_lines.append(fmt(emojis.rockets_cost, item_stats.rockets_cost, ItemStat.rockets_cost))
    if item_stats.advance or item_stats.retreat:
        stats_lines.append(
            f"{emojis.jump} **{i18n.get_message(locale, 'item-lookup-jump-required')}**"
        )
    if stats_lines and stats_lines[-1] == "":
        stats_lines.pop()

    return stats_lines


@plugin.listener(Event.message_interaction)
async def on_item_lookup_interaction(inter: ui.MessageInteraction) -> None:
    if not inter.data.custom_id.startswith("item-lookup"):
        return

    component, ctx = parse_component_id(inter.data.custom_id)
    locale = i18n.get_locale(inter)
    item = get_item(ctx)

    # NOTE: using __replace__ directly due to copy.replace(**kwargs: Any)
    match component:
        case ComponentIds.stage_select:
            assert inter.values
            [option_value] = inter.values
            new_stage_index = int(option_value, 16)

            if new_stage_index > ctx.stage_index:
                ctx = ctx.__replace__(stage_index=new_stage_index, level_index=0, levels_page=1)

            else:
                total_levels = len(item.stages[new_stage_index].levels)
                ctx = ctx.__replace__(
                    stage_index=new_stage_index,
                    level_index=total_levels - 1,
                    levels_page=ui.PaginatedSelect.option_to_page_count(total_levels),
                )

        case ComponentIds.level_select:
            assert inter.values
            [option_value] = inter.values

            if option_value == "$u":
                ctx = ctx.__replace__(levels_page=ctx.levels_page - 1)

            elif option_value == "$d":
                ctx = ctx.__replace__(levels_page=ctx.levels_page + 1)

            else:
                ctx = ctx.__replace__(level_index=int(option_value))

        case ComponentIds.buffs_button:
            ctx = ctx.__replace__(buffs_enabled=ctx.buffs_enabled ^ True)

        case ComponentIds.avg_button:
            ctx = ctx.__replace__(damage_average=ctx.damage_average ^ True)

        case ComponentIds.titan_button:
            ctx = ctx.__replace__(damage_vs_titan=ctx.damage_vs_titan ^ True)

        case _:
            msg = f"Unknown component: {component!r}, {ctx!r}"
            raise RuntimeError(msg)

    embed, layout = get_item_summary(locale, item, ctx)
    if __debug__:
        debug_message(embed, layout)
    await inter.response.edit_message(embed=embed, components=layout)


@plugin.slash_command(guild_ids=CONFIG.test_guild_ids)
async def item_raw(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
    legacy: bool = False,
) -> None:
    """Lookup raw item stats.

    Parameters
    ----------
    name:
        The name of the item.
    type:
        Limit suggestions to this type.
    element:
        Limit suggestions to this element.
    rarity:
        Remove suggestions below this rarity.
    legacy:
        Show legacy items.
    """
    for item in packs.filter_items(type, element, rarity, legacy):
        if item.name == name:
            break

    else:
        msg = i18n.get_message(i18n.get_locale(inter), "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    await inter.response.send_message(f"`{item!r:.{MessageLimits.content - 2}}`", ephemeral=True)


def str_type(type: sm.Item.Type) -> str:
    return type.name.replace("_", " ").lower()


def str_elem(element: sm.Item.Element) -> str:
    return element.name.capitalize()


@plugin.slash_command()
async def compare(
    inter: CommandInteraction,
    item_a_name: str = commands.Param(name="item1", autocomplete=item_name_autocomplete),
    item_b_name: str = commands.Param(name="item2", autocomplete=item_name_autocomplete),
) -> None:
    """Interactive comparison between two items. {{ COMPARE }}

    Parameters
    ----------
    item_a_name:
        First item to compare. {{ COMPARE_FIRST }}
    item_b_name:
        Second item to compare. {{ COMPARE_SECOND }}
    """  # noqa: D400
    locale = i18n.get_locale(inter)
    item_a = None
    item_b = None

    match item_a, item_b:
        case None, None:
            msg = "Items not found."
            raise commands.UserInputError(msg)
        case None, _:  # pyright: ignore[reportUnnecessaryComparison]
            msg = "Item1 not found."
            raise commands.UserInputError(msg)
        case _, None:  # pyright: ignore[reportUnnecessaryComparison]
            msg = "Item2 not found."
            raise commands.UserInputError(msg)
        case _:
            pass

    if item_a.element is item_b.element:
        desc_builder = io.StringIO()
        desc_builder.write(str_elem(item_a.element))

        if item_a.type is item_b.type:
            desc_builder.write(" ")
            type_ = str_type(item_a.type)
            desc_builder.write(type_)

            if not type_.endswith("s"):  # legs do end with s
                desc_builder.write("s")

        else:
            desc_builder.write(f" {str_type(item_a.type)} / {str_type(item_b.type)}")

        desc = desc_builder.getvalue()
        color = COLORS.elements[item_a.element]

    else:
        desc = (
            f"{str_elem(item_a.element)} {str_type(item_a.type)}"
            f" | {str_elem(item_b.element)} {str_type(item_b.type)}"
        )
        color = inter.author.color

    embed = Embed(title=f"{item_a.name} vs {item_b.name}", description=desc, color=color)

    sikrit_footer(embed, locale)

    await inter.response.send_message(embed=embed, ephemeral=True)
    return  # FIXME

    from .item_lookup import item_compare_view  # noqa: PLC0415

    store = ui.callback_store(inter)
    layout = item_compare_view(store, embed, item_a, item_b, locale)
    await inter.response.send_message(embed=embed, components=layout, ephemeral=True)
    async with Defer(shield=True) as defer:
        defer(inter.edit_original_response, components=None)
        await store.listen(timeout=CONFIG.user_input_timeout)


setup, teardown = plugin.create_extension_handlers()
