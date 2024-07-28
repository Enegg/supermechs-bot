import io
from itertools import zip_longest

from disnake import ButtonStyle, Embed, Locale, MessageInteraction, ui

import i18n
from assets import ASSETS
from devtools import debug_footer
from discord_utils import SPACE
from discord_utils.ui import ActionButton, ToggleButton
from discord_utils.ui.store import ComponentStore
from sm.asset_utils import item_transform_range

from .helpers import get_row_width, iter_formatted_stats, try_shorten

from supermechs.api import MAX_SHOP, ItemData, Stat
from supermechs.tools.stats import buff_stats, max_stats
from supermechs.utils import contains_any_of


def item_view(
    store: ComponentStore,
    embed: Embed,
    item: ItemData,
    locale: Locale,
    compact: bool,
) -> ui.Components[ui.MessageUIComponent]:
    populate_fields = compact_fields if compact else default_fields
    populate_fields(embed, item, False, False, locale)
    gettext = i18n.get_gettext(locale)

    if __debug__:
        debug_footer(embed)

    @store.bind(ToggleButton(label="Buffs", custom_id=store.make_id()))
    async def buff_button(inter: MessageInteraction) -> None:
        buff_button.toggle()
        await update(inter)

    @store.bind(ToggleButton(label="Damage average", custom_id=store.make_id()))
    async def avg_button(inter: MessageInteraction) -> None:
        avg_button.toggle()
        await update(inter)

    @store.bind(
        ActionButton(label=gettext("ui-quit"), style=ButtonStyle.red, custom_id=store.make_id())
    )
    async def quit_button(inter: MessageInteraction) -> None:
        store.stop()
        await inter.response.defer()

    async def update(inter: MessageInteraction) -> None:
        embed.clear_fields()
        populate_fields(embed, item, buff_button.on, avg_button.on, locale)

        if __debug__:
            debug_footer(embed, replace=True)

        await inter.response.edit_message(embed=embed, components=layout)

    layout = [[buff_button, quit_button]]

    if contains_any_of(
        item.start_stage.min(),
        Stat.physical_damage,
        Stat.electric_damage,
        Stat.explosive_damage,
    ):
        layout[0].insert(1, avg_button)

    return layout


def default_fields(
    embed: Embed, item: ItemData, buffs_enabled: bool, avg: bool, locale: Locale
) -> None:
    """Fills embed with detailed info about an item."""
    embed.add_field("Transform range:", item_transform_range(item), inline=False)

    spaced = False
    string = io.StringIO()
    cost_stats = (Stat.backfire, Stat.heat_generation, Stat.energy_cost)

    stats = max_stats(item)

    if buffs_enabled:
        stats = buff_stats(stats, MAX_SHOP)
        # TODO: differences

    for stat, str_value in iter_formatted_stats(stats, avg):
        if not spaced and stat in cost_stats:
            string.write("\n")
            spaced = True

        string.write(f"{ASSETS.stats[stat].emoji} **{str_value}** {i18n.get_stat_name(locale, stat)}\n")

    if item.tags.require_jump:
        string.write(f"{ASSETS.stats[Stat.jump].emoji} **Jumping required**")

    embed.add_field("Stats:", string.getvalue(), inline=False)


def compact_fields(
    embed: Embed,
    item: ItemData,
    buffs_enabled: bool,
    avg: bool,
    locale: Locale,
) -> None:
    """Fills embed with reduced info about an item."""
    del locale
    lines: list[str] = []

    stats = max_stats(item)

    if buffs_enabled:
        stats = buff_stats(stats, MAX_SHOP)

    for stat_key, str_value in iter_formatted_stats(stats, avg, 0):
        lines.append(f"{ASSETS.stats[stat_key].emoji} **{str_value}**")

    if item.tags.require_jump:
        lines.append(f"{ASSETS.stats[Stat.jump].emoji}❗")

    line_count = len(lines)
    div = get_row_width(line_count, 4)

    field_text = ("\n".join(lines[i : i + div]) for i in range(0, line_count, div))
    transform_range = item_transform_range(item)

    for name, field in zip_longest((transform_range,), field_text, fillvalue=SPACE):
        embed.add_field(name, field)


def item_compare_view(
    store: ComponentStore,
    embed: Embed,
    item_a: ItemData,
    item_b: ItemData,
    locale: Locale,
) -> ui.Components[ui.MessageUIComponent]:
    gettext = i18n.get_gettext(locale)
    max_item_stats = (max_stats(item_a), max_stats(item_b))

    @store.bind(ToggleButton(label=gettext("item-compare-ui-buffs"), custom_id=store.make_id()))
    async def buffs_button(inter: MessageInteraction) -> None:
        buffs_button.toggle()
        update()
        await inter.response.edit_message(embed=embed, components=layout)

    @store.bind(
        ActionButton(label=gettext("ui-quit"), style=ButtonStyle.red, custom_id=store.make_id())
    )
    async def quit_button(inter: MessageInteraction) -> None:
        await inter.response.defer()
        store.stop()

    def update() -> None:
        stats_a, stats_b = max_item_stats

        if buffs_button.on:
            stats_a = buff_stats(stats_a, MAX_SHOP)
            stats_b = buff_stats(stats_b, MAX_SHOP)

        raise NotImplementedError
        name_field, first_field, second_field = stats_to_fields(stats_a, stats_b, locale=locale)

        if require_jump := item_a.tags.require_jump:
            first_field.append("❕")

        if item_b.tags.require_jump:
            second_field.append("❕")
            require_jump = True

        if require_jump:
            emoji = ASSETS.stats[Stat.jump].emoji
            name_field.append(f"{emoji} **{gettext('item-compare-jump-required')}**")

        modify_field_at = embed.set_field_at if embed._fields else embed.insert_field_at

        modify_field_at(0, gettext("item-compare-stat-header"), "\n".join(name_field))
        modify_field_at(1, try_shorten(item_a.name), "\n".join(first_field))
        modify_field_at(2, try_shorten(item_b.name), "\n".join(second_field))

        if __debug__:
            debug_footer(embed)

    layout = [[buffs_button, quit_button]]
    return layout