import datetime as dt
import logging
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from discord import markdown as md
from disnake import MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import EMOJIS, ICONS, Colors
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import ELEMENT_CHOICES, SLOT_CHOICES, TIER_CHOICES
from app.core import AppState
from app.devtools import debug_components
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from resources import HttpResource

from .helpers import (
    format_float,
    format_stats,
    has_buff_affected_stats,
    has_damage,
    has_damage_spread,
    item_transform_range,
)

import supermechs.all as sm
from supermechs import stats

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
    slot: str | None = commands.Param(None, choices=SLOT_CHOICES),
    element: str | None = commands.Param(None, choices=ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=TIER_CHOICES),
) -> None:
    """Lookup item info. {{ ITEM }}

    Parameters
    ----------
    name:
        The name of the item. {{ ITEM_NAME }}
    slot:
        Limit suggestions to this item slot. {{ ITEM_SLOT }}
    element:
        Limit suggestions to this element. {{ ITEM_ELEMENT }}
    rarity:
        Remove suggestions below this rarity. {{ ITEM_TIER }}
    """  # noqa: D400
    gettext = i18n.get_gettext(inter)

    for item in packs.filter_items(AppState.item_pack, slot, element, rarity, False):
        if item.name == name:
            break

    else:
        msg = gettext("unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    stage_index = len(item.stages) - 1
    levels = item.stages[stage_index].levels
    ctx = UIContext(
        item_id=item.id,
        stage_index=stage_index,
        level_index=len(levels) - 1,
        levels_page=ui.option_to_page_count(len(levels)),
    )
    container = get_item_summary(gettext, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.send_message(
        components=container, flags=MessageFlags(is_components_v2=True)
    )


async def on_reloaded_lookup_interaction(
    inter: ui.MessageInteraction, logger: logging.Logger
) -> None:
    component, ctx = parse_component_id(inter.data.custom_id)
    gettext = i18n.get_gettext(inter)
    item_pack = AppState.item_pack
    # If the bot (re)starts with a new item pack, and a summary of an item from previous
    # pack persists, interaction with it may lead to following scenarios:
    try:
        item = item_pack.reloaded_items[ctx.item_id]

    # 1. The ID is invalid. Can't do much but disabling the view and/or sending a message:
    except KeyError:
        await inter.response.edit_message(components=ui.Container(
            ui.TextDisplay(gettext("item-lookup-item-not-available", command=get_mention("item"))),
            accent_colour=Colors.error,
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
        await inter.response.edit_message(components=get_item_summary(gettext, item, ctx))
        # we cannot easily tell if the item has not changed. (save for parsing the message and comparing item names)
        # If it did, it's going to confuse the user, so lets inform them (even if it didn't)
        await inter.followup.send(
            gettext("item-lookup-item-changed-info", command=get_mention("item")),
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

    container = get_item_summary(gettext, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.edit_message(components=container)


def get_item_stats(item: sm.Item, ctx: UIContext, /) -> sm.ItemStats:
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


def get_item_summary(gettext: i18n.GetText, item: sm.Item, ctx: UIContext) -> ui.Container:
    stage = item.stages[ctx.stage_index]
    levels = stage.levels
    item_stats = get_item_stats(item, ctx)

    # ------------------------------------- title, description -------------------------------------
    subtitle_parts: list[str] = []

    if item.element is not sm.Item.Element.other:
        subtitle_parts.append(item.element.name)

    subtitle_parts.append(item.slot_id.name.replace("_", " "))
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
        if power_required >= 1000 and power_required % 100 == 0:  # noqa: PLR2004
            power_str = format_float(power_required / 1000, 1) + "k"

        else:
            power_str = f"{power_required:,}"

        # energizing
        power_line = [
            f"{gettext('item-lookup-power-required')}: **{power_str}**{EMOJIS.stat_energy_capacity}"
        ]
        common_pks, rare_pks = power_required_as_power_kits(power_required)

        power_kits: list[str] = []

        if rare_pks:
            power_kits.append(f"**{rare_pks}**×{EMOJIS.power_kit_rare}")  # noqa: RUF001

        if common_pks:
            power_kits.append(f"**{common_pks}**×{EMOJIS.power_kit_common}")  # noqa: RUF001

        if power_kits:
            power_line.append(f"({' '.join(power_kits)})")

        title_lines.append("".join(power_line))

    title = ui.TextDisplay("\n".join(title_lines))
    container, add_component = ui.container(accent_color=Colors.get_element(item.element))

    match ICONS.get_item_slot(item.slot_id):
        case HttpResource(url):
            add_component(ui.Section(title, accessory=ui.thumbnail(url)))

        case _:
            add_component(title)

    # ------------------------------------------- stats --------------------------------------------
    if item.subtype is sm.Item.Subtype.power_kit:
        boost_power = levels[ctx.level_index].power_contribution
        add_component(ui.TextDisplay(
                f"{EMOJIS.stat_energy_capacity} **{boost_power}** {gettext('boost-power')}"
        ))  # fmt: skip
    else:
        stats_lines, costs_lines = format_stats(item_stats, gettext, avg=ctx.damage_average)

        if stats_lines or costs_lines:
            stats_part = "\n".join(stats_lines)
            costs_part = "\n".join(costs_lines)
            add_component(ui.TextDisplay(
                f"**{gettext('item-lookup-stats-header')}:**\n{stats_part or costs_part}"
            ))  # fmt: skip
            if stats_part and costs_part:
                add_component(ui.Separator(divider=False))
                add_component(ui.TextDisplay(costs_part))
        else:
            add_component(ui.TextDisplay(f"-# {gettext('item-lookup-no-stats')}"))

    # ------------------------------------------- image --------------------------------------------
    if (sprite_url := gfx.get_image_url((item.id, stage.tier))) is not None:
        add_component(ui.MediaGallery(ui.media_gallery_item(sprite_url)))
    else:
        add_component(ui.TextDisplay(f"*{gettext('item-lookup-no-image')}*"))

    # ------------------------------------------ buttons -------------------------------------------
    button_row: list[ui.ActionButton] = []

    if has_buff_affected_stats(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-buffs"),
            style=ui.ButtonStyle.green if ctx.buffs_enabled else ui.ButtonStyle.gray,
            emoji="⚔️",
            custom_id=make_component_id(ComponentIds.buffs_button, ctx),
        ))  # fmt: skip
    if has_damage_spread(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-avg"),
            style=ui.ButtonStyle.green if ctx.damage_average else ui.ButtonStyle.gray,
            emoji=EMOJIS.get_element(item.element).to_partial(),
            custom_id=make_component_id(ComponentIds.avg_button, ctx),
        ))  # fmt: skip
    if has_damage(item_stats):
        button_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-vs-titans"),
            style=ui.ButtonStyle.green if ctx.buffs_enabled and ctx.damage_vs_titan else ui.ButtonStyle.gray,
            disabled=not ctx.buffs_enabled,
            emoji=EMOJIS.get_element(item.element).to_partial(),
            custom_id=make_component_id(ComponentIds.titan_button, ctx),
        ))  # fmt: skip
    if button_row:
        add_component(ui.ActionRow(*button_row))

    # ---------------------------------------- stage select ----------------------------------------
    if len(item.stages) > 1:
        add_component(ui.ActionRow(ui.StringSelect(
            options=[
                ui.SelectOption(
                    label=gettext.get_tier_name(stage.tier).capitalize(),
                    value=f"{i:x}",
                    emoji=EMOJIS.get_tier(stage.tier, hollow=i != ctx.stage_index).to_partial(),
                    default=i == ctx.stage_index,
                )
                for i, stage in enumerate(item.stages)
            ],
            placeholder=gettext("item-lookup-ui-tier-select-placeholder"),
            custom_id=make_component_id(ComponentIds.stage_select, ctx),
        )))  # fmt: skip

    # ---------------------------------------- level select ----------------------------------------
    if len(levels) > 1:
        page_index = ctx.levels_page - 1
        start, end = ui.get_options_slice_for_page(len(levels), page_index)
        level_options: list[ui.SelectOption] = []
        if start != 0:
            prev_start, prev_end = ui.get_options_slice_for_page(len(levels), page_index - 1)
            level_options.append(ui.SelectOption(
                label=gettext("item-lookup-ui-select-next-label", min=prev_start + 1, max=prev_end),
                value="$u",
                emoji="🔺",
            ))  # fmt: skip
        level_options += [
            ui.SelectOption(
                label=gettext("item-lookup-ui-level-select-label", level=level.level),
                value=str(i),
                default=i == ctx.level_index,
            )
            for i, level in enumerate(
                levels if start == 0 and end == len(levels) else levels[start:end], start=start
            )
        ]
        if end != len(levels):
            next_start, next_end = ui.get_options_slice_for_page(len(levels), page_index + 1)
            level_options.append(ui.SelectOption(
                label=gettext("item-lookup-ui-select-next-label", min=next_start + 1, max=next_end),
                value="$d",
                emoji="🔻",
            ))  # fmt: skip

        add_component(ui.ActionRow(ui.StringSelect(
            options=level_options,
            placeholder=gettext("item-lookup-ui-level-select-placeholder"),
            custom_id=make_component_id(ComponentIds.level_select, ctx),
        )))  # fmt: skip

    # ---------------------------------------- release date ----------------------------------------
    if item.release_date is not None:
        when = "Released" if item.release_date < dt.datetime.now(tz=dt.UTC) else "Releases"
        add_component(ui.TextDisplay(
            f"-# {when} {md.format_dt(item.release_date, "R")}"
        ))  # fmt: skip

    return container
