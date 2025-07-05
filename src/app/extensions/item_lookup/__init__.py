from collections import abc
from typing import NamedTuple

from app.disnake_types import CommandInteraction
from discord import ComponentLimits
from disnake import Color, Event, Locale, MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, EMOJIS, get_slot_icon
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import (
    ELEMENT_CHOICES,
    LEGACY_ELEMENT_CHOICES,
    LEGACY_TIER_CHOICES,
    TIER_CHOICES,
    TYPE_CHOICES,
)
from app.devtools import debug_components
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from app.plugins_factory import create_plugin
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
USES_EMOJI_THRESHOLD = 4


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


@plugin.slash_command(name="item")
async def item_lookup(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
) -> None:
    """Lookup item info. {{ ITEM }}

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
    """  # noqa: D400
    for item in packs.filter_items(type, element, rarity, False):
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
        level_index=len(levels) - 1,
        levels_page=ui.option_to_page_count(len(levels)),
    )
    container = get_item_summary(i18n.get_locale(inter), item, ctx)
    await inter.response.send_message(
        components=container, flags=MessageFlags(is_components_v2=True)
    )


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
            value=f"{i}",
            default=i == selected_level_index,
        )
        for i, level in enumerate(levels, start=start)
    ]


def make_option_up(locale: Locale, /) -> ui.SelectOption:
    return ui.SelectOption(
        label=i18n.get_message(locale, "item-lookup-ui-select-up-label"), value="$u", emoji="🔺"
    )


def make_option_down(locale: Locale, /) -> ui.SelectOption:
    return ui.SelectOption(
        label=i18n.get_message(locale, "item-lookup-ui-select-down-label"), value="$d", emoji="🔻"
    )


def get_item_summary(locale: Locale, item: sm.IItem, ctx: ItemLookupUIContext) -> ui.Container:
    gettext = i18n.get_gettext(locale)
    stage = item.stages[ctx.stage_index]
    levels = stage.levels
    item_stats = get_item_stats(item, ctx)
    name_parts: list[str] = []

    if ctx.legacy:
        name_parts.append("legacy")

    if item.element is not sm.Item.Element.other:
        name_parts.append(item.element.name)

    name_parts.append(item.type.name.replace("_", " "))
    name_parts[0] = name_parts[0].capitalize()

    power_level = (
        "max"
        if ctx.stage_index == len(item.stages) - 1 and ctx.level_index == len(levels) - 1
        else str(levels[ctx.level_index].level)
    )
    title = ui.TextDisplay(
        f"### {item.name}\n"
        f"{' '.join(name_parts)}\n"
        f"{item_transform_range(item, ctx.stage_index)}\n"
        f"{gettext('item-lookup-power-level')}: **{power_level}**"
    )
    components: list[ui.ContainerChildUIComponent] = []

    match get_slot_icon(item.type):
        case HttpResource(url):
            components.append(ui.Section(title, accessory=ui.thumbnail(str(url))))

        case _:
            components.append(title)

    stats_lines, costs_lines = format_stats(item_stats, locale, avg=ctx.damage_average)

    if stats_lines or costs_lines:
        stats_part = "\n".join(stats_lines)
        costs_part = "\n".join(costs_lines)
        components.append(ui.Section(
            ui.TextDisplay(
                f"**{gettext('item-lookup-stats-header')}:**\n{stats_part or costs_part}"
            ),
            accessory=ui.ActionButton(
                label=gettext("item-lookup-ui-buffs"),
                style=ui.ButtonStyle.green if ctx.buffs_enabled else ui.ButtonStyle.gray,
                custom_id=make_component_id(ComponentIds.buffs_button, ctx),
            ),
        ))  # fmt: skip
        if stats_part and costs_part:
            components.append(ui.Separator(divider=False))
            components.append(ui.TextDisplay(costs_part))

    else:
        components.append(ui.TextDisplay(f"-# {gettext('item-lookup-no-stats')}"))

    if (sprite_url := gfx.get_image_url((item.id, stage.tier))) is not None:
        components.append(ui.MediaGallery(ui.media_gallery_item(sprite_url)))
    else:
        components.append(ui.TextDisplay(f"*{gettext('item-lookup-no-image')}*"))

    if len(item.stages) > 1:
        stage_options = [
            ui.SelectOption(
                label=gettext(f"tier-{stage.tier.name}").capitalize(),  # noqa: INT001
                value=f"{i:x}",
                emoji=EMOJIS.tiers[stage.tier],
                default=i == ctx.stage_index,
            )
            for i, stage in enumerate(item.stages)
        ]
        components.append(ui.ActionRow(ui.StringSelect(
            options=stage_options,
            placeholder="Select tier",
            custom_id=make_component_id(ComponentIds.stage_select, ctx),
        )))  # fmt: skip

    if len(levels) <= ComponentLimits.select_options:
        level_options = make_level_options(locale, levels, ctx.level_index)

    elif ctx.levels_page == 1:
        level_options = make_level_options(
            locale, levels[: ComponentLimits.select_options - 1], ctx.level_index
        )
        level_options.append(make_option_down(locale))

    elif ctx.levels_page == ui.option_to_page_count(len(levels)):
        offset = (ComponentLimits.select_options - 2) * (ctx.levels_page - 1) + 1
        level_options = [
            make_option_up(locale),
            *make_level_options(locale, levels[offset:], ctx.level_index, offset),
        ]

    else:
        size = ComponentLimits.select_options - 2
        offset = size * (ctx.levels_page - 1) + 1
        level_options = [
            make_option_up(locale),
            *make_level_options(locale, levels[offset : offset + size], ctx.level_index, offset),
            make_option_down(locale),
        ]

    components.append(ui.ActionRow(ui.StringSelect(
        options=level_options,
        placeholder=gettext("item-lookup-ui-select-placeholder"),
        custom_id=make_component_id(ComponentIds.level_select, ctx),
    )))  # fmt: skip
    button_row: list[ui.ActionButton] = []

    if has_damage_spread(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-avg"),
            style=ui.ButtonStyle.green if ctx.damage_average else ui.ButtonStyle.gray,
            custom_id=make_component_id(ComponentIds.avg_button, ctx),
        ))  # fmt: skip

    if not ctx.legacy and has_damage(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-vs-titans"),
            style=ui.ButtonStyle.green if ctx.damage_vs_titan else ui.ButtonStyle.gray,
            custom_id=make_component_id(ComponentIds.titan_button, ctx),
        ))  # fmt: skip

    if button_row:
        components.append(ui.ActionRow(*button_row))

    return ui.Container(*components, accent_colour=COLORS.elements[item.element])


def format_stats(
    item_stats: sm.IItemStats, locale: Locale, *, avg: bool
) -> tuple[list[str], list[str]]:
    def fmt(emoji: str, value: int | str, stat_key: ItemStat, /) -> str:
        return f"{emoji} **{value}** {i18n.get_stat_name(locale, stat_key)}"

    format_damage: abc.Callable[[int, int], str] = (
        format_damage_average if avg else format_damage_default
    )

    stats_lines: list[str] = []
    costs_lines: list[str] = []
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
    if item_stats.repair:
        stats_lines.append(fmt(emojis.repair, item_stats.repair, ItemStat.repair))
    if item_stats.uses:
        count = 1 if item_stats.uses > USES_EMOJI_THRESHOLD else item_stats.uses
        costs_lines.append(fmt(emojis.uses * count, item_stats.uses, ItemStat.uses))
    if item_stats.backfire:
        costs_lines.append(fmt(emojis.backfire, item_stats.backfire, ItemStat.backfire))
    if item_stats.heat_generation:
        costs_lines.append(
            fmt(emojis.heat_generation, item_stats.heat_generation, ItemStat.heat_generation)
        )
    if item_stats.energy_cost:
        costs_lines.append(fmt(emojis.energy_cost, item_stats.energy_cost, ItemStat.energy_cost))
    if item_stats.bullets_cost:
        costs_lines.append(fmt(emojis.bullets_cost, item_stats.bullets_cost, ItemStat.bullets_cost))
    if item_stats.rockets_cost:
        costs_lines.append(fmt(emojis.rockets_cost, item_stats.rockets_cost, ItemStat.rockets_cost))
    if item_stats.advance or item_stats.retreat:
        costs_lines.append(
            f"{emojis.jump} **{i18n.get_message(locale, 'item-lookup-jump-required')}**"
        )
    return stats_lines, costs_lines


@plugin.listener(Event.message_interaction)
async def on_item_lookup_interaction(inter: ui.MessageInteraction) -> None:
    if not inter.data.custom_id.startswith("item-lookup"):
        return

    component, ctx = parse_component_id(inter.data.custom_id)
    locale = i18n.get_locale(inter)
    item_pack = packs.get_item_pack()
    bank = item_pack.legacy_items if ctx.legacy else item_pack.reloaded_items

    # If the bot (re)starts with a new item pack, and a summary of an item from previous
    # pack persists, interaction with it may lead to following scenarios:
    try:
        item = bank[ctx.item_id]

    # 1. The ID is invalid. Can't do much but disabling the view and/or sending a message:
    except KeyError:
        cmd_mention = get_mention("legacy-item" if ctx.legacy else "item")
        await inter.response.edit_message(components=ui.Container(
            ui.TextDisplay(
                "⚠️ This item is no longer available.\n"
                "-# Hint: the item pack might have been changed. "
                f"Try searching it with {cmd_mention} again."
            ),
            accent_colour=Color(0xFF0000),
        ))  # fmt: skip
        return

    # 2. The ID is valid. It may point to the same or a different item; the data may contain fewer stages/levels.
    # We will assume that if either of the indices doesn't match, it's a different item:
    if (
        len(item.stages) < ctx.stage_index
        or len(item.stages[ctx.stage_index].levels) < ctx.level_index
    ):
        valid_stage_index = min(ctx.stage_index, len(item.stages) - 1)
        valid_level_index = min(ctx.level_index, len(item.stages[valid_stage_index].levels) - 1)
        # TODO: deduce levels_page from level_index
        ctx = ctx.__replace__(
            stage_index=valid_stage_index, level_index=valid_level_index, levels_page=0
        )
        await inter.response.edit_message(components=get_item_summary(locale, item, ctx))
        # we cannot easily tell if the item has not changed. (save for parsing the message and comparing item names)
        # If it did, it's going to confuse the user, so lets inform them (even if it didn't)
        cmd_mention = get_mention("legacy-item" if ctx.legacy else "item")
        await inter.followup.send(
            "The summary you've interacted with was made using a different item pack.\n"
            f"If the item shown has changed, try searching it with {cmd_mention} again.",
            ephemeral=True,
        )
        return

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
                    levels_page=ui.option_to_page_count(total_levels),
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

        case unknown_id:
            plugin.logger.warning("item-lookup - unknown component: %r", unknown_id)

    container = get_item_summary(locale, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.edit_message(components=container)


@plugin.slash_command(name="legacy-item")
async def legacy_item_lookup(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    type: str | None = commands.Param(None, choices=TYPE_CHOICES),
    element: str | None = commands.Param(None, choices=LEGACY_ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=LEGACY_TIER_CHOICES),
) -> None:
    """Lookup legacy item info.

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
    """
    for item in packs.filter_items(type, element, rarity, True):
        if item.name == name:
            break

    else:
        msg = i18n.get_message(i18n.get_locale(inter), "unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    ctx = ItemLookupUIContext(
        item_id=item.id,
        stage_index=0,
        level_index=0,
        levels_page=0,
        legacy=True,
    )
    await inter.response.send_message(
        components=get_item_summary(i18n.get_locale(inter), item, ctx),
        flags=MessageFlags(is_components_v2=True),
    )


setup, teardown = plugin.create_extension_handlers()
