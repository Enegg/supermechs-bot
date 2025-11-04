import logging
from collections import abc
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from discord import ComponentLimits
from disnake import Color, Locale, MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, EMOJIS, get_slot_icon
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import ELEMENT_CHOICES, TIER_CHOICES, TYPE_CHOICES
from app.devtools import debug_components
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from resources import HttpResource

from .helpers import format_stats, has_damage, has_damage_spread, item_transform_range

import dupermechs.all as sm
from dupermechs import stats

COMMON_PK_POWER = 10_000
RARE_PK_POWER = 50_000


class UIContext(NamedTuple):
    item_id: sm.Item.Id
    stage_index: int
    level_index: int
    levels_page: int
    damage_average: bool = False
    buffs_enabled: bool = False
    damage_vs_titan: bool = False


class ComponentIds:
    __slots__ = ()

    prefix: Final = "item-lookup"

    stage_select: Final = "stages"
    level_select: Final = "levels"
    buffs_button: Final = "buffs"
    avg_button: Final = "avg"
    titan_button: Final = "dvt"

    type AnyId = Literal["stages", "levels", "buffs", "avg", "dvt"]


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
    ctx = UIContext(
        item_id=item.id,
        stage_index=stage_index,
        level_index=len(levels) - 1,
        levels_page=ui.option_to_page_count(len(levels)),
    )
    container = get_item_summary(i18n.get_locale(inter), item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.send_message(
        components=container, flags=MessageFlags(is_components_v2=True)
    )


async def on_reloaded_lookup_interaction(
    inter: ui.MessageInteraction, logger: logging.Logger
) -> None:
    component, ctx = parse_component_id(inter.data.custom_id)
    locale = i18n.get_locale(inter)
    item_pack = packs.get_item_pack()
    # If the bot (re)starts with a new item pack, and a summary of an item from previous
    # pack persists, interaction with it may lead to following scenarios:
    try:
        item = item_pack.reloaded_items[ctx.item_id]

    # 1. The ID is invalid. Can't do much but disabling the view and/or sending a message:
    except KeyError:
        await inter.response.edit_message(components=ui.Container(
            ui.TextDisplay(
                "⚠️ This item is no longer available.\n"
                "-# Hint: the item pack might have been changed. "
                f"Try searching it with {get_mention('item')} again."
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
        await inter.followup.send(
            "The summary you've interacted with was made using a different item pack.\n"
            f"If the item shown has changed, try searching it with {get_mention('item')} again.",
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
            ctx = ctx.__replace__(buffs_enabled=not ctx.buffs_enabled)

        case ComponentIds.avg_button:
            ctx = ctx.__replace__(damage_average=not ctx.damage_average)

        case ComponentIds.titan_button:
            ctx = ctx.__replace__(damage_vs_titan=not ctx.damage_vs_titan)

        case _:
            logger.warning("%s - unknown component: %r", ComponentIds.prefix, component)

    container = get_item_summary(locale, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.edit_message(components=container)


def get_item_stats(item: sm.IItem, ctx: UIContext, /) -> sm.IItemStats:
    base_stats = item.stages[ctx.stage_index].levels[ctx.level_index].stats

    if not ctx.buffs_enabled:
        return base_stats

    total = [base_stats, stats.bonus_item_stats(base_stats, MAXED_ARENA_BUFFS)]

    if ctx.damage_vs_titan:
        total.append(stats.bonus_damage_vs_titan(base_stats, MAXED_ARENA_BUFFS))

    return stats.combine(total)


def make_component_id(component: str, ctx: UIContext) -> str:
    flags = ctx.damage_average | ctx.buffs_enabled << 1 | ctx.damage_vs_titan << 2
    return f"{ComponentIds.prefix}:{component}:{ctx.item_id:x}:{ctx.stage_index}:{ctx.level_index}:{ctx.levels_page}:{flags:x}"


def parse_component_id(id: str, /) -> tuple[ComponentIds.AnyId | str, UIContext]:
    _, component, item_id, stage_index, level_index, levels_page, flags = id.split(":", 6)
    flags = int(flags, 16)
    return (
        component,
        UIContext(
            item_id=sm.Item.Id(int(item_id, 16)),
            stage_index=int(stage_index),
            level_index=int(level_index),
            levels_page=int(levels_page),
            damage_average=flags & 1 == 1,
            buffs_enabled=flags >> 1 & 1 == 1,
            damage_vs_titan=flags >> 2 & 1 == 1,
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
            label=i18n.get_message(locale, "item-lookup-ui-level-select-label", level=level.level),
            value=str(i),
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


def power_required_as_power_kits(power: int, /) -> tuple[int, int]:
    rare_pks, power = divmod(power, RARE_PK_POWER)

    if power >= RARE_PK_POWER * 0.9:
        rare_pks += 1
        common_pks = 0

    else:
        common_pks, power = divmod(power, COMMON_PK_POWER)

        if power >= COMMON_PK_POWER * 0.8:
            common_pks += 1

    return common_pks, rare_pks


def get_item_summary(locale: Locale, item: sm.IItem, ctx: UIContext) -> ui.Container:
    gettext = i18n.get_gettext(locale)
    stage = item.stages[ctx.stage_index]
    levels = stage.levels
    item_stats = get_item_stats(item, ctx)
    subtitle_parts: list[str] = []

    if item.element is not sm.Item.Element.other:
        subtitle_parts.append(item.element.name)

    subtitle_parts.append(item.type.name.replace("_", " "))
    subtitle_parts[0] = subtitle_parts[0].capitalize()

    power_level = (
        "max"
        if ctx.stage_index == len(item.stages) - 1 and ctx.level_index == len(levels) - 1
        else str(levels[ctx.level_index].level)
    )

    title_lines = [
        f"## {item.name}",
        f"*{' '.join(subtitle_parts)}*",
        f"-# {item_transform_range(item, ctx.stage_index)}",
        f"{gettext('item-lookup-power-level')}: **{power_level}**",
    ]

    if power_required := levels[ctx.level_index].power_required:
        # energizing
        power_line = [
            f"{gettext('item-lookup-power-required')}: **{power_required:,}**{EMOJIS.stats.energy_capacity}"
        ]
        common_pks, rare_pks = power_required_as_power_kits(power_required)

        power_kits: list[str] = []

        if rare_pks:
            power_kits.append(f"**{rare_pks}**×{EMOJIS.power_kits.rare}")  # noqa: RUF001

        if common_pks:
            power_kits.append(f"**{common_pks}**×{EMOJIS.power_kits.common}")  # noqa: RUF001

        if power_kits:
            power_line.append(f"({' '.join(power_kits)})")

        title_lines.append("".join(power_line))

    title = ui.TextDisplay("\n".join(title_lines))
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
                emoji="⚔️",
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

    if has_damage(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-vs-titans"),
            style=ui.ButtonStyle.green if ctx.buffs_enabled and ctx.damage_vs_titan else ui.ButtonStyle.gray,
            disabled=not ctx.buffs_enabled,
            emoji=EMOJIS.elements[item.element],
            custom_id=make_component_id(ComponentIds.titan_button, ctx),
        ))  # fmt: skip

    if button_row:
        components.append(ui.ActionRow(*button_row))

    return ui.Container(*components, accent_colour=COLORS.elements[item.element])
