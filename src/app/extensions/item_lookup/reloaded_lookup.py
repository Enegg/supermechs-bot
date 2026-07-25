import datetime as dt
import logging
import math
from typing import Final, Literal, NamedTuple

from app.disnake_types import CommandInteraction
from discord import markdown as md
from discord.emoji import AnyEmoji
from disnake import MessageFlags
from disnake.ext import commands

from app import i18n, ui
from app.assets import EMOJIS, ICONS, NULL_EMOJI, Colors, NoneEmoji
from app.commands.autocompleters import item_name_autocomplete
from app.commands.mentions import get_mention
from app.commands.params import ELEMENT_CHOICES, SLOT_CHOICES, TIER_CHOICES
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
    has_damage,
    has_damage_spread,
    item_transform_range,
    move_last_between,
)

import supermechs.all as sm
from supermechs import stats


class FoodPower:
    common_item: Final = 400
    rare_item: Final = 1_760
    common_pk: Final = 10_000
    rare_pk: Final = 50_000

    common_pk_to_pk: Final = common_pk // 10 * 11  # +10%
    rare_pk_to_pk: Final = rare_pk // 10 * 11  # +10%


LINES_PER_BUTTON = 2
MAX_RANK = 13
MAX_LEVEL = 50


class UIContext(NamedTuple):
    item_id: sm.Item.Id
    stage_index: int
    level_index: int
    levels_page: int
    damage_average: bool = False
    buffs_enabled: bool = False
    damage_vs_titan: bool = False


class ComponentIds:
    prefix: Final = "item-lookup"

    stage_select: Final = "stages"
    level_select: Final = "levels"
    buffs_button: Final = "buffs"
    avg_button: Final = "avg"
    titan_button: Final = "dvt"

    type AnyId = Literal["stages", "levels", "buffs", "avg", "dvt"]


def level_to_rank_emoji[T](level_index: int, default: T = NULL_EMOJI) -> AnyEmoji | T:
    factor = MAX_RANK / MAX_LEVEL
    new_index = math.floor(level_index * factor)
    return EMOJIS.get_rank(new_index, default)


def divmod_round(x: int, y: int, f: float, /) -> tuple[int, int]:
    """Like divmod, but if `x%y >= y*f`, returns `(a//b+1, 0)`."""
    a, b = divmod(x, y)
    if b >= y * f:
        return a + 1, 0
    return a, b


async def slash_item(
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

    for item in packs.filter_items(slot, element, rarity, False):
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
    item_pack = packs.get_item_pack()
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


class FoodItems(NamedTuple):
    common_pks: int = 0
    rare_pks: int = 0
    common_items: int = 0
    rare_items: int = 0
    leftover: int = 0


def food_items_required_for_power(power: int, /, target_is_pk: bool = False) -> FoodItems:
    rare_pks, power = divmod_round(
        power, FoodPower.rare_pk_to_pk if target_is_pk else FoodPower.rare_pk, 0.95
    )
    common_pks, power = divmod_round(
        power, FoodPower.common_pk_to_pk if target_is_pk else FoodPower.common_pk, 0.95
    )
    rare_items, power = divmod_round(power, FoodPower.rare_item, 0.8)
    common_items, power = divmod_round(power, FoodPower.common_item, 0.75)
    return FoodItems(
        common_pks=common_pks,
        rare_pks=rare_pks,
        common_items=common_items,
        rare_items=rare_items,
        leftover=power,
    )


def get_item_summary(gettext: i18n.GetText, item: sm.Item, ctx: UIContext) -> ui.Container:
    stage = item.stages[ctx.stage_index]
    levels = stage.levels
    item_stats = get_item_stats(item, ctx)
    container, add_component = ui.container(accent_color=Colors.get_tier(stage.tier))

    # ------------------------------------- title, description -------------------------------------
    subtitle_parts: list[str] = []

    if item.element is not sm.Item.Element.other:
        subtitle_parts.append(item.element.name)

    subtitle_parts.append(item.slot_id.name.replace("_", " "))
    subtitle_parts[0] = subtitle_parts[0].capitalize()

    is_max_level: Final = ctx.level_index == len(levels) - 1
    is_max_stage: Final = ctx.stage_index == len(item.stages) - 1
    power_level = "max" if is_max_stage and is_max_level else str(levels[ctx.level_index].level)
    title_lines = [
        f"## {item.name}",
        f"*{' '.join(subtitle_parts)}*",
        f"-# {item_transform_range(item, ctx.stage_index)}",
        f"{gettext('item-lookup-power-level')}: **{power_level}** {level_to_rank_emoji(ctx.level_index)}",
    ]

    # - - - - - - - - - - - - - - - - - - - - power required - - - - - - - - - - - - - - - - - - - -
    if power_required := levels[ctx.level_index].power_required:
        # energizing
        power_line = (
            f"{gettext('item-lookup-power-required')}: "
            f"**{format_real_to_metric(power_required)}**"
            f"{embed_emoji_name(EMOJIS.stat_power, power_required)}"
        )
        food_items = food_items_required_for_power(
            power_required, item.subtype is sm.Item.Subtype.power_kit
        )
        power_kits: list[str] = []

        if food_items.rare_pks:
            power_kits.append(f"**{food_items.rare_pks}**×{EMOJIS.power_kit_rare}")  # noqa: RUF001
        if food_items.common_pks:
            power_kits.append(f"**{food_items.common_pks}**×{EMOJIS.power_kit_common}")  # noqa: RUF001
        if food_items.rare_items:
            power_kits.append(f"**{food_items.rare_items}**×{EMOJIS.card_rare}")  # noqa: RUF001
        if food_items.common_items:
            power_kits.append(f"**{food_items.common_items}**×{EMOJIS.card_common}")  # noqa: RUF001
        if food_items.leftover and power_kits:
            power_kits.append(f"+**{food_items.leftover}**")

        if power_kits:
            power_line += f"({' '.join(power_kits)})"

        title_lines.append(power_line)

    # - - - - - - - - - - - - - - - - - - - - - gold costs - - - - - - - - - - - - - - - - - - - - -
    if cumulative_gold_cost := sum(levels[i].upgrade_gold_cost for i in range(ctx.level_index)):
        title_lines.append(
            f"{gettext('item-lookup-total-upgrade-cost')}: "
            f"**{format_real_to_metric(cumulative_gold_cost)}** "
            f"{embed_emoji_name(EMOJIS.currency_gold, cumulative_gold_cost)}"
        )

    if is_max_level and not is_max_stage:
        if stage.evolution_gold_cost:
            title_lines.append(
                f"{gettext('item-lookup-evolution-cost')}: "
                f"**{format_real_to_metric(stage.evolution_gold_cost)}** "
                f"{embed_emoji_name(EMOJIS.currency_gold, stage.evolution_gold_cost)}"
            )
        elif stage.ascension_gold_cost:
            title_lines.append(
                f"{gettext('item-lookup-ascension-cost')}: "
                f"**{format_real_to_metric(stage.ascension_gold_cost)}** "
                f"{embed_emoji_name(EMOJIS.currency_gold, stage.ascension_gold_cost)}"
            )

    title = ui.TextDisplay("\n".join(title_lines))

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

            if has_damage(item_stats):
                move_last_between(current_lines, stats_lines, LINES_PER_BUTTON)
                add_component(ui.Section(
                    ui.TextDisplay("\n".join(current_lines)),
                    accessory=ui.ActionButton(
                        label=gettext("item-lookup-ui-damage-vs-titans"),
                        style=ui.ButtonStyle.green if ctx.buffs_enabled and ctx.damage_vs_titan else ui.ButtonStyle.gray,
                        disabled=not ctx.buffs_enabled,
                        emoji=EMOJIS.get_element(item.element).to_partial(),
                        custom_id=make_component_id(ComponentIds.titan_button, ctx),
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
    if (sprite_url := gfx.get_image_url((item.id, stage.tier))) is not None:
        add_component(ui.MediaGallery(ui.media_gallery_item(sprite_url)))
    else:
        add_component(ui.TextDisplay(f"*{gettext('item-lookup-no-image')}*"))

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
                emoji=level_to_rank_emoji(i, NoneEmoji).to_partial(),
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

    # ------------------------------------- tips, release date -------------------------------------
    tip_display: list[str] = []

    if power_required >= METRIC_FORMAT_THRESHOLD or cumulative_gold_cost >= METRIC_FORMAT_THRESHOLD:
        tip_display.append(
            f"-# tip: press {EMOJIS.stat_power} or {EMOJIS.currency_gold} to view the exact values!"
        )
    if item.release_date is not None:
        when = gettext(
            "item-lookup-released"
            if item.release_date < dt.datetime.now(tz=dt.UTC)
            else "item-lookup-releases"
        )
        tip_display.append(f"-# {when} {md.format_dt(item.release_date, 'R')}")

    if tip_display:
        add_component(ui.TextDisplay("\n".join(tip_display)))
    return container
