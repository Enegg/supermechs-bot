import logging
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from discord import ComponentLimits
from disnake import MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import EMOJIS, ICONS, Colors, NoneEmoji
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import LEGACY_ELEMENT_CHOICES, LEGACY_TIER_CHOICES, SLOT_CHOICES
from app.devtools import debug_components
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx, packs
from resources import HttpResource

from .helpers import (
    METRIC_FORMAT_THRESHOLD,
    embed_emoji_name,
    format_real_to_metric,
    format_stats,
    has_buff_affected_stats,
    has_damage_spread,
    move_last_between,
)

import supermechs.all as sm
from supermechs import stats

LEGACY_PK_POWER = 76_800
LINES_PER_BUTTON = 2


class UIContext(NamedTuple):
    item_id: sm.Item.Id
    level_index: int
    damage_average: bool = False
    buffs_enabled: bool = False


class ComponentIds:
    prefix: Final = "legacy-item-lookup"

    level_select: Final = "levels"
    buffs_button: Final = "buffs"
    avg_button: Final = "avg"

    type AnyId = Literal["levels", "buffs", "avg"]


async def slash_legacy_item(
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
            accent_colour=Colors.error,
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
    tier_emoji = emoji if (emoji := EMOJIS.get_card(tier)) is not None else EMOJIS.get_tier(tier)
    rank_emoji = EMOJIS.get_rank(ctx.level_index)
    title_lines = [
        f"## {item.name}",
        f"*{' '.join(subtitle_parts)}* {tier_emoji}",
        f"{gettext('item-lookup-power-level')}: **{power_level}** {rank_emoji}",
    ]

    if power_required := levels[ctx.level_index].power_required:
        # energizing
        power_line = [
            f"{gettext('item-lookup-power-required')}: "
            f"**{format_real_to_metric(power_required)}**"
            f"{embed_emoji_name(EMOJIS.stat_power, power_required)}"
        ]
        legacy_pks = power_required_as_legacy_power_kits(power_required)

        if legacy_pks:
            power_line.append(f"(**{legacy_pks}**×{EMOJIS.power_kit_common})")  # noqa: RUF001

        title_lines.append("".join(power_line))

    if cumulative_gold_cost := sum(levels[i].upgrade_gold_cost for i in range(ctx.level_index)):
        title_lines.append(
            f"{gettext('item-lookup-total-upgrade-cost')}: "
            f"**{format_real_to_metric(cumulative_gold_cost)}** "
            f"{EMOJIS.currency_gold}"
        )

    title = ui.TextDisplay("\n".join(title_lines))
    container, add_component = ui.container(accent_color=Colors.get_tier(tier))

    match ICONS.get_item_slot(item.slot_id):
        case HttpResource(url):
            add_component(ui.Section(title, accessory=ui.thumbnail(url)))

        case _:
            add_component(title)

    # ------------------------------------------- stats --------------------------------------------
    if item.subtype is sm.Item.Subtype.power_kit:
        boost_power = levels[ctx.level_index].power_contribution
        add_component(ui.TextDisplay(
                f"{EMOJIS.stat_power} **{boost_power}** {gettext('boost-power')}"
        ))  # fmt: skip
    else:
        stats_lines, costs_lines = format_stats(item, item_stats, gettext, avg=ctx.damage_average)

        if not (stats_lines or costs_lines):
            add_component(ui.TextDisplay(f"-# {gettext('item-lookup-no-stats')}"))

        elif not stats_lines:
            ...  # TODO

        else:
            stats_lines.reverse()
            current_lines: list[str] = [f"**{gettext('item-lookup-stats-header')}:**"]

            if has_buff_affected_stats(item_stats):
                move_last_between(current_lines, stats_lines, LINES_PER_BUTTON)
                add_component(ui.Section(
                    ui.TextDisplay("\n".join(current_lines)),
                    accessory=ui.ActionButton(
                        label=gettext("item-lookup-ui-buffs"),
                        style=ui.ButtonStyle.green
                        if ctx.buffs_enabled
                        else ui.ButtonStyle.gray,
                        emoji="⚔️",
                        custom_id=make_component_id(ComponentIds.buffs_button, ctx),
                    ),
                ))  # fmt: skip
                current_lines.clear()

            if has_damage_spread(item_stats):
                move_last_between(current_lines, stats_lines, LINES_PER_BUTTON)
                add_component(ui.Section(
                    ui.TextDisplay("\n".join(current_lines)),
                    accessory=ui.ActionButton(
                        label=gettext("item-lookup-ui-damage-avg"),
                        style=ui.ButtonStyle.green if ctx.damage_average else ui.ButtonStyle.gray,
                        emoji=EMOJIS.get_element(item.element).to_partial(),
                        custom_id=make_component_id(ComponentIds.avg_button, ctx),
                    ),
                ))  # fmt: skip
                current_lines.clear()

            current_lines += reversed(stats_lines)
            if current_lines:
                add_component(ui.TextDisplay("\n".join(current_lines)))
            if current_lines and costs_lines:
                add_component(ui.Separator(divider=False))
                add_component(ui.TextDisplay("\n".join(costs_lines)))

    # ------------------------------------------- image --------------------------------------------
    if (sprite_url := gfx.get_image_url((item.id, tier))) is not None:
        add_component(ui.MediaGallery(ui.media_gallery_item(sprite_url)))
    else:
        add_component(ui.TextDisplay(f"*{gettext('item-lookup-no-image')}*"))

    # ---------------------------------------- level select ----------------------------------------
    if len(levels) > 1:
        add_component(ui.ActionRow(ui.StringSelect(
            options=[
                ui.SelectOption(
                    label=gettext("item-lookup-ui-level-select-label", level=level.level),
                    value=str(i),
                    emoji=EMOJIS.get_rank(i, NoneEmoji).to_partial(),
                    default=i == ctx.level_index,
                )
                for i, level in enumerate(levels)
            ],
            placeholder=gettext("item-lookup-ui-level-select-placeholder"),
            custom_id=make_component_id(ComponentIds.level_select, ctx),
        )))  # fmt: skip

    # --------------------------------------------- tip --------------------------------------------
    if power_required >= METRIC_FORMAT_THRESHOLD:
        add_component(
            ui.TextDisplay(f"-# tip: press {EMOJIS.stat_power} to view exact power required!")
        )
    return container
