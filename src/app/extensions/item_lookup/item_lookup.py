from disnake import Embed, Locale

from app import i18n, ui
from app.assets import EMOJIS
from app.devtools import debug_message
from app.gamerules import MAXED_ARENA_BUFFS

from .helpers import try_shorten

import dupermechs.all as sm
from dupermechs import stats


def max_stats(item: sm.IItem, /) -> sm.IItemStats:
    return item.stages[-1].levels[-1].stats


def item_compare_view(
    store: ui.CallbackStore,
    embed: Embed,
    item_a: sm.IItem,
    item_b: sm.IItem,
    locale: Locale,
) -> ui.MessageComponents:
    gettext = i18n.get_gettext(locale)
    max_item_stats = (max_stats(item_a), max_stats(item_b))

    @store.bind(ui.ToggleButton(label=gettext("item-compare-ui-buffs"), custom_id=store.make_id()))
    async def buffs_button(inter: ui.MessageInteraction) -> None:
        buffs_button.toggle()
        update()
        await inter.response.edit_message(embed=embed, components=layout)

    def update() -> None:
        stats_a, stats_b = max_item_stats

        if buffs_button.on:
            stats_a = stats.bonus_item_stats(stats_a, MAXED_ARENA_BUFFS)
            stats_b = stats.bonus_item_stats(stats_b, MAXED_ARENA_BUFFS)

        raise NotImplementedError
        name_field, first_field, second_field = stats_to_fields(stats_a, stats_b, locale=locale)

        if require_jump := item_a.tags.require_jump:
            first_field.append("❕")

        if item_b.tags.require_jump:
            second_field.append("❕")
            require_jump = True

        if require_jump:
            emoji = EMOJIS.stats.jump
            name_field.append(f"{emoji} **{gettext('item-compare-jump-required')}**")

        modify_field_at = embed.set_field_at if embed._fields else embed.insert_field_at

        modify_field_at(0, gettext("item-compare-stat-header"), "\n".join(name_field))
        modify_field_at(1, try_shorten(item_a.name), "\n".join(first_field))
        modify_field_at(2, try_shorten(item_b.name), "\n".join(second_field))

        if __debug__:
            debug_message(embed)

    layout = [[buffs_button]]
    return layout  # noqa: RET504 https://github.com/astral-sh/ruff/issues/14052
