import logging
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from discord import ComponentLimits
from disnake import MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import COLORS, EMOJIS, get_slot_icon
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import LEGACY_ELEMENT_CHOICES, LEGACY_TIER_CHOICES, SLOT_CHOICES
from app.devtools import debug_components
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from resources import HttpResource

from .helpers import format_float, format_stats, has_buff_affected_stats, has_damage_spread

import dupermechs.all as sm
from dupermechs import stats

LEGACY_PK_POWER = 76_800


class UIContext(NamedTuple):
    item_id: sm.Item.Id
    level_index: int
    damage_average: bool = False
    buffs_enabled: bool = False


class ComponentIds:
    __slots__ = ()

    prefix: Final = "legacy-item-lookup"

    level_select: Final = "levels"
    buffs_button: Final = "buffs"
    avg_button: Final = "avg"

    type AnyId = Literal["levels", "buffs", "avg"]


async def legacy_item_lookup(
    inter: CommandInteraction,
    name: str = commands.Param(autocomplete=item_name_autocomplete),
    slot: str | None = commands.Param(None, choices=SLOT_CHOICES),
    element: str | None = commands.Param(None, choices=LEGACY_ELEMENT_CHOICES),
    rarity: str | None = commands.Param(None, choices=LEGACY_TIER_CHOICES),
) -> None:
    """Lookup legacy item info.

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
    """
    gettext = i18n.get_gettext(inter)

    for item in packs.filter_items(slot, element, rarity, True):
        if item.name == name:
            break

    else:
        msg = gettext("unknown-item-name", name=name)
        raise commands.UserInputError(msg)

    ctx = UIContext(item_id=item.id, level_index=0)
    container = get_item_summary(gettext, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.send_message(
        components=container, flags=MessageFlags(is_components_v2=True)
    )


async def on_legacy_lookup_interaction(
    inter: ui.MessageInteraction, logger: logging.Logger
) -> None:
    component, ctx = parse_component_id(inter.data.custom_id)
    gettext = i18n.get_gettext(inter)
    item_pack = packs.get_item_pack()
    # If the bot (re)starts with a new item pack, and a summary of an item from previous
    # pack persists, interaction with it may lead to following scenarios:
    try:
        item = item_pack.legacy_items[ctx.item_id]

    # 1. The ID is invalid. Can't do much but disabling the view and/or sending a message:
    except KeyError:
        await inter.response.edit_message(components=ui.Container(
            ui.TextDisplay(
                gettext("item-lookup-item-not-available", command=get_mention("legacy-item"))
            ),
            accent_colour=COLORS.error,
        ))  # fmt: skip
        return

    # 2. The ID is valid. It may point to the same or a different item; the data may contain fewer levels.
    # We will assume that if the index doesn't match, it's a different item:
    if len(item.stages[0].levels) < ctx.level_index:
        valid_level_index = min(ctx.level_index, len(item.stages[0].levels) - 1)
        ctx = ctx.__replace__(level_index=valid_level_index)
        await inter.response.edit_message(components=get_item_summary(gettext, item, ctx))
        # we cannot easily tell if the item has not changed. (save for parsing the message and comparing item names)
        # If it did, it's going to confuse the user, so lets inform them (even if it didn't)
        await inter.followup.send(
            gettext("item-lookup-item-changed-info", command=get_mention("legacy-item")),
            ephemeral=True,
        )
        return

    # NOTE: using __replace__ directly due to copy.replace(**kwargs: Any)
    match component:
        case ComponentIds.level_select:
            assert inter.values
            [option_value] = inter.values
            ctx = ctx.__replace__(level_index=int(option_value))

        case ComponentIds.buffs_button:
            ctx = ctx.__replace__(buffs_enabled=not ctx.buffs_enabled)

        case ComponentIds.avg_button:
            ctx = ctx.__replace__(damage_average=not ctx.damage_average)

        case _:
            logger.warning("%s - unknown component: %r", ComponentIds.prefix, component)

    container = get_item_summary(gettext, item, ctx)
    if __debug__:
        debug_components(container)
    await inter.response.edit_message(components=container)


def get_item_stats(item: sm.Item, ctx: UIContext, /) -> sm.ItemStats:
    base_stats = item.stages[0].levels[ctx.level_index].stats

    if not ctx.buffs_enabled:
        return base_stats

    return stats.combine((base_stats, stats.bonus_item_stats(base_stats, MAXED_ARENA_BUFFS)))


def make_component_id(component: str, ctx: UIContext) -> str:
    flags = ctx.damage_average | ctx.buffs_enabled << 1
    return f"{ComponentIds.prefix}:{component}:{ctx.item_id:x}:{ctx.level_index}:{flags:x}"


def parse_component_id(id: str, /) -> tuple[ComponentIds.AnyId | str, UIContext]:
    _, component, item_id, level_index, flags = id.split(":", 4)
    flags = int(flags, 16)
    return (
        component,
        UIContext(
            item_id=sm.Item.Id(int(item_id, 16)),
            level_index=int(level_index),
            damage_average=flags & 1 == 1,
            buffs_enabled=flags >> 1 & 1 == 1,
        ),
    )


def power_required_as_legacy_power_kits(power: int, /) -> int:
    legacy_pks, power = divmod(power, LEGACY_PK_POWER)

    if power >= LEGACY_PK_POWER * 0.9:
        legacy_pks += 1

    return legacy_pks


def get_item_summary(gettext: i18n.GetText, item: sm.Item, ctx: UIContext) -> ui.Container:
    tier = item.stages[0].tier
    levels = item.stages[0].levels
    assert len(levels) <= ComponentLimits.string_select_options  # TODO: guard this better
    item_stats = get_item_stats(item, ctx)

    # ------------------------------------- title, description -------------------------------------
    subtitle_parts: list[str] = ["Legacy"]

    if item.element is not sm.Item.Element.other:
        subtitle_parts.append(item.element.name)

    subtitle_parts.append(item.slot_id.name.replace("_", " "))

    power_level = (
        "max" if ctx.level_index == len(levels) - 1 else str(levels[ctx.level_index].level)
    )
    tier_emoji = emoji if (emoji := EMOJIS.cards[tier]) is not None else EMOJIS.tiers[tier]
    title_lines = [
        f"## {item.name}",
        f"*{' '.join(subtitle_parts)}* {tier_emoji}",
        f"{gettext('item-lookup-power-level')}: **{power_level}**",
    ]

    if power_required := levels[ctx.level_index].power_required:
        if power_required >= 1000 and power_required % 100 == 0:  # noqa: PLR2004
            power_str = format_float(power_required / 1000, 1) + "k"

        else:
            power_str = f"{power_required:,}"

        # energizing
        power_line = [
            f"{gettext('item-lookup-power-required')}: **{power_str}**{EMOJIS.stats.energy_capacity}"
        ]
        legacy_pks = power_required_as_legacy_power_kits(power_required)

        if legacy_pks:
            power_line.append(f"(**{legacy_pks}**×{EMOJIS.power_kits.common})")  # noqa: RUF001

        title_lines.append("".join(power_line))

    title = ui.TextDisplay("\n".join(title_lines))
    container = ui.Container(accent_colour=COLORS.elements[item.element])

    match get_slot_icon(item.slot_id):
        case HttpResource(url):
            container.children.append(ui.Section(title, accessory=ui.thumbnail(str(url))))

        case _:
            container.children.append(title)

    # ------------------------------------------- stats --------------------------------------------
    stats_lines, costs_lines = format_stats(item_stats, gettext, avg=ctx.damage_average)

    if (
        item.slot_id is sm.Item.Slot.kit
        and not stats_lines
        and (boost_power := levels[ctx.level_index].power_contribution)
    ):
        stats_lines.append(
            f"{EMOJIS.stats.energy_capacity} **{boost_power}** {gettext('boost-power')}"
        )
    if stats_lines or costs_lines:
        stats_part = "\n".join(stats_lines)
        costs_part = "\n".join(costs_lines)
        container.children.append(ui.TextDisplay(
            f"**{gettext('item-lookup-stats-header')}:**\n{stats_part or costs_part}"
        ))  # fmt: skip
        if stats_part and costs_part:
            container.children.append(ui.Separator(divider=False))
            container.children.append(ui.TextDisplay(costs_part))
    else:
        container.children.append(ui.TextDisplay(f"-# {gettext('item-lookup-no-stats')}"))

    # ------------------------------------------ buttons -------------------------------------------
    buttons_row: list[ui.ActionButton] = []

    if has_buff_affected_stats(item_stats):
        buttons_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-buffs"),
            style=ui.ButtonStyle.green if ctx.buffs_enabled else ui.ButtonStyle.gray,
            emoji="⚔️",
            custom_id=make_component_id(ComponentIds.buffs_button, ctx),
        ))  # fmt: skip
    if has_damage_spread(item_stats):
        buttons_row.append(ui.ActionButton(
            label=gettext("item-lookup-ui-damage-avg"),
            style=ui.ButtonStyle.green if ctx.damage_average else ui.ButtonStyle.gray,
            emoji=EMOJIS.elements[item.element],
            custom_id=make_component_id(ComponentIds.avg_button, ctx),
        ))  # fmt: skip

    if buttons_row:
        container.children.append(ui.ActionRow(*buttons_row))

    # ------------------------------------------- image --------------------------------------------
    if (sprite_url := gfx.get_image_url((item.id, tier))) is not None:
        container.children.append(ui.MediaGallery(ui.media_gallery_item(sprite_url)))
    else:
        container.children.append(ui.TextDisplay(f"*{gettext('item-lookup-no-image')}*"))

    # ---------------------------------------- level select ----------------------------------------
    container.children.append(ui.ActionRow(ui.StringSelect(
        options=[
            ui.SelectOption(
                label=gettext("item-lookup-ui-level-select-label", level=level.level),
                value=str(i),
                default=i == ctx.level_index,
            )
            for i, level in enumerate(levels)
        ],
        placeholder=gettext("item-lookup-ui-level-select-placeholder"),
        custom_id=make_component_id(ComponentIds.level_select, ctx),
    )))  # fmt: skip

    return container
