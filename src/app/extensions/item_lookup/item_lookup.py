from collections import abc
from typing import Final

import attrs

from disnake import Embed, Locale

from app import i18n, ui
from app.assets import COLORS, EMOJIS
from app.devtools import debug_footer
from app.gamerules import MAXED_ARENA_BUFFS
from app.managers import gfx
from app.models.ids import SpriteId

from .helpers import try_shorten

import dupermechs.all as sm
from dupermechs import stats
from dupermechs.enums import ItemStat


def item_transform_range(item: sm.IItem, /, stage: int = -1) -> str:
    str_range = [EMOJIS.tiers[stage.tier] for stage in item.stages]
    str_range[stage] = f"({str_range[stage]})"
    return "".join(str_range)


def has_damage_spread(stats: sm.IItemStats, /) -> bool:
    return (
        stats.physical_damage != stats.physical_damage_addon
        or stats.explosive_damage != stats.explosive_damage_addon
        or stats.electric_damage != stats.electric_damage_addon
    )


def has_damage(stats: sm.IItemStats, /) -> bool:
    return stats.physical_damage != 0 or stats.explosive_damage != 0 or stats.electric_damage != 0


def requires_jump(stats: sm.IItemStats, /) -> bool:
    return stats.advance != 0 or stats.retreat != 0


@attrs.define(kw_only=True)
class ItemUIContext:
    item: Final[sm.IItem]
    locale: Final[Locale]
    stage_index: int
    level_index: int
    icon_url: str | None = None
    damage_average: bool = False
    buffs_enabled: bool = False
    damage_vs_titan: bool = False

    def get_stage(self) -> sm.IItemStage:
        return self.item.stages[self.stage_index]

    def get_sprite_url(self) -> str | None:
        return gfx.get_image_url(SpriteId(self.item.id, self.get_stage().tier))

    def get_stats(self) -> sm.IItemStats:
        base_stats = self.get_stage().levels[self.level_index].stats
        total = [base_stats]

        if self.buffs_enabled:
            total.append(stats.bonus_item_stats(base_stats, MAXED_ARENA_BUFFS))

        if self.damage_vs_titan:
            total.append(stats.bonus_damage_vs_titan(base_stats, MAXED_ARENA_BUFFS))

        return stats.combine(total)

    def get_max_level(self) -> int:
        return len(self.get_stage().levels) - 1

    def get_level_options(self) -> abc.Sequence[ui.SelectOption]:
        return [
            ui.SelectOption(
                label=f"{i18n.get_message(self.locale, 'item-lookup-ui-level-select-label')} {level.level}",
                value=str(n),
            )
            for n, level in enumerate(self.get_stage().levels)
        ]

    @property
    def display_level(self) -> int:
        return self.level_index + 1

    def get_embed(self) -> Embed:
        return get_embed_default(self)


def get_embed_default(ctx: ItemUIContext, /) -> Embed:
    from .helpers import format_damage, format_damage_average, format_range

    def format_line(emoji: str, value: int | str, stat_key: ItemStat) -> str:
        return f"{emoji} **{value}** {i18n.get_stat_name(ctx.locale, stat_key)}"

    if ctx.damage_average:
        format_damage = format_damage_average

    gettext = i18n.get_gettext(ctx.locale)
    name_parts: list[str] = []
    # TODO: if <legacy>: add "Legacy" prefix

    # Legacy explosive side weapon
    # Reliktowa wybuchowa broń boczna

    # Legacy electric torso
    # Reliktowy elektryczny tors

    if ctx.item.element is not sm.Item.Element.other:
        name_parts.append(ctx.item.element.name)

    name_parts.append(ctx.item.type.name.replace("_", " "))

    name_parts[0] = name_parts[0].capitalize()
    desc_lines: list[str] = [
        " ".join(name_parts),
        item_transform_range(ctx.item, ctx.stage_index),
        f"{gettext('item-lookup-power-level')}: **{ctx.get_stage().levels[ctx.level_index].level}**",
    ]
    spaced = False
    stats_lines: list[str] = []
    item_stats = ctx.get_stats()

    if item_stats.weight:
        stats_lines.append(format_line(EMOJIS.stats.weight, item_stats.weight, ItemStat.weight))
    if item_stats.hit_points:
        stats_lines.append(
            format_line(EMOJIS.stats.hit_points, item_stats.hit_points, ItemStat.hit_points)
        )
    if item_stats.energy_capacity:
        stats_lines.append(
            format_line(
                EMOJIS.stats.energy_capacity, item_stats.energy_capacity, ItemStat.energy_capacity
            )
        )
    if item_stats.energy_regeneration:
        stats_lines.append(
            format_line(
                EMOJIS.stats.energy_regeneration,
                item_stats.energy_regeneration,
                ItemStat.energy_regeneration,
            )
        )
    if item_stats.heat_capacity:
        stats_lines.append(
            format_line(
                EMOJIS.stats.heat_capacity, item_stats.heat_capacity, ItemStat.heat_capacity
            )
        )
    if item_stats.heat_cooling:
        stats_lines.append(
            format_line(EMOJIS.stats.heat_cooling, item_stats.heat_cooling, ItemStat.heat_cooling)
        )
    if item_stats.physical_resistance:
        stats_lines.append(
            format_line(
                EMOJIS.stats.physical_resistance,
                item_stats.physical_resistance,
                ItemStat.physical_resistance,
            )
        )
    if item_stats.explosive_resistance:
        stats_lines.append(
            format_line(
                EMOJIS.stats.explosive_resistance,
                item_stats.explosive_resistance,
                ItemStat.explosive_resistance,
            )
        )
    if item_stats.electric_resistance:
        stats_lines.append(
            format_line(
                EMOJIS.stats.electric_resistance,
                item_stats.electric_resistance,
                ItemStat.electric_resistance,
            )
        )
    if item_stats.bullets_capacity:
        stats_lines.append(
            format_line(
                EMOJIS.stats.bullets_capacity,
                item_stats.bullets_capacity,
                ItemStat.bullets_capacity,
            )
        )
    if item_stats.rockets_capacity:
        stats_lines.append(
            format_line(
                EMOJIS.stats.rockets_capacity,
                item_stats.rockets_capacity,
                ItemStat.rockets_capacity,
            )
        )
    if item_stats.physical_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.physical_damage,
                format_damage(item_stats.physical_damage, item_stats.physical_damage_addon),
                ItemStat.physical_damage,
            )
        )
    if item_stats.physical_resistance_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.physical_resistance_damage,
                item_stats.physical_resistance_damage,
                ItemStat.physical_resistance_damage,
            )
        )
    if item_stats.electric_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.electric_damage,
                format_damage(item_stats.electric_damage, item_stats.electric_damage_addon),
                ItemStat.electric_damage,
            )
        )
    if item_stats.energy_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.energy_damage, item_stats.energy_damage, ItemStat.energy_damage
            )
        )
    if item_stats.energy_capacity_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.energy_capacity_damage,
                item_stats.energy_capacity_damage,
                ItemStat.energy_capacity_damage,
            )
        )
    if item_stats.regeneration_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.regeneration_damage,
                item_stats.regeneration_damage,
                ItemStat.regeneration_damage,
            )
        )
    if item_stats.electric_resistance_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.electric_resistance_damage,
                item_stats.electric_resistance_damage,
                ItemStat.electric_resistance_damage,
            )
        )
    if item_stats.explosive_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.explosive_damage,
                format_damage(item_stats.explosive_damage, item_stats.explosive_damage_addon),
                ItemStat.explosive_damage,
            )
        )
    if item_stats.heat_damage:
        stats_lines.append(
            format_line(EMOJIS.stats.heat_damage, item_stats.heat_damage, ItemStat.heat_damage)
        )
    if item_stats.heat_capacity_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.heat_capacity_damage,
                item_stats.heat_capacity_damage,
                ItemStat.heat_capacity_damage,
            )
        )
    if item_stats.cooling_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.cooling_damage, item_stats.cooling_damage, ItemStat.cooling_damage
            )
        )
    if item_stats.explosive_resistance_damage:
        stats_lines.append(
            format_line(
                EMOJIS.stats.explosive_resistance_damage,
                item_stats.explosive_resistance_damage,
                ItemStat.explosive_resistance_damage,
            )
        )
    if item_stats.walk:
        stats_lines.append(format_line(EMOJIS.stats.walk, item_stats.walk, ItemStat.walk))
    if item_stats.jump:
        stats_lines.append(format_line(EMOJIS.stats.jump, item_stats.jump, ItemStat.jump))
    if item_stats.range:
        stats_lines.append(
            format_line(
                EMOJIS.stats.range,
                format_range(item_stats.range, item_stats.range_addon),
                ItemStat.range,
            )
        )
    if item_stats.push:
        stats_lines.append(format_line(EMOJIS.stats.push, item_stats.push, ItemStat.push))
    if item_stats.pull:
        stats_lines.append(format_line(EMOJIS.stats.pull, item_stats.pull, ItemStat.pull))
    if item_stats.recoil:
        stats_lines.append(format_line(EMOJIS.stats.recoil, item_stats.recoil, ItemStat.recoil))
    if item_stats.advance:
        stats_lines.append(format_line(EMOJIS.stats.advance, item_stats.advance, ItemStat.advance))
    if item_stats.retreat:
        stats_lines.append(format_line(EMOJIS.stats.retreat, item_stats.retreat, ItemStat.retreat))
    if item_stats.uses:
        stats_lines.append(format_line(EMOJIS.stats.uses, item_stats.uses, ItemStat.uses))
    if item_stats.repair:
        stats_lines.append(format_line(EMOJIS.stats.repair, item_stats.repair, ItemStat.repair))
    spaced = False
    if item_stats.backfire:
        if not spaced:
            stats_lines.append("")
            spaced = True
        stats_lines.append(
            format_line(EMOJIS.stats.backfire, item_stats.backfire, ItemStat.backfire)
        )
    if item_stats.heat_generation:
        if not spaced:
            stats_lines.append("")
            spaced = True
        stats_lines.append(
            format_line(
                EMOJIS.stats.heat_generation, item_stats.heat_generation, ItemStat.heat_generation
            )
        )
    if item_stats.energy_cost:
        if not spaced:
            stats_lines.append("")
            spaced = True
        stats_lines.append(
            format_line(EMOJIS.stats.energy_cost, item_stats.energy_cost, ItemStat.energy_cost)
        )
    if item_stats.bullets_cost:
        if not spaced:
            stats_lines.append("")
            spaced = True
        stats_lines.append(
            format_line(EMOJIS.stats.bullets_cost, item_stats.bullets_cost, ItemStat.bullets_cost)
        )
    if item_stats.rockets_cost:
        if not spaced:
            stats_lines.append("")
            spaced = True
        stats_lines.append(
            format_line(EMOJIS.stats.rockets_cost, item_stats.rockets_cost, ItemStat.rockets_cost)
        )
    if requires_jump(item_stats):
        stats_lines.append(f"{EMOJIS.stats.jump} **{gettext('item-lookup-jump-required')}**")

    if not stats_lines:
        desc_lines.append(f"-# {gettext('item-lookup-no-stats')}")

    sprite_url = ctx.get_sprite_url()
    embed = (
        Embed(
            title=ctx.item.name,
            description="\n".join(desc_lines),
            color=COLORS.elements[ctx.item.element],
        )
        .set_thumbnail(ctx.icon_url)
        .set_image(sprite_url)
    )
    if sprite_url is None:
        embed.set_footer(text=gettext("item-lookup-no-image"))
    if stats_lines:
        embed.add_field(
            f"{gettext('item-lookup-stats-header')}:", "\n".join(stats_lines), inline=False
        )

    return embed


def item_view(
    store: ui.CallbackStore,
    ctx: ItemUIContext,
) -> ui.MessageComponents:
    async def respond(inter: ui.MessageInteraction) -> None:
        await inter.response.edit_message(embed=ctx.get_embed(), components=layout)

    gettext = i18n.get_gettext(ctx.locale)

    @store.bind(ui.ToggleButton(label=gettext("item-lookup-ui-buffs"), custom_id=store.make_id()))
    async def buff_button(inter: ui.MessageInteraction) -> None:
        buff_button.toggle()
        ctx.buffs_enabled = buff_button.on
        await respond(inter)

    button_row = [buff_button]
    item_stats = ctx.get_stats()

    if has_damage_spread(item_stats):

        @store.bind(
            ui.ToggleButton(label=gettext("item-lookup-ui-damage-avg"), custom_id=store.make_id())
        )
        async def avg_button(inter: ui.MessageInteraction) -> None:
            avg_button.toggle()
            ctx.damage_average = avg_button.on
            await respond(inter)

        button_row.append(avg_button)

    if has_damage(item_stats):

        @store.bind(
            ui.ToggleButton(
                label=gettext("item-lookup-ui-damage-vs-titans"), custom_id=store.make_id()
            )
        )
        async def titan_dmg_button(inter: ui.MessageInteraction) -> None:
            titan_dmg_button.toggle()
            ctx.damage_vs_titan = titan_dmg_button.on
            await respond(inter)

        button_row.append(titan_dmg_button)

    all_options = ctx.get_level_options()
    all_options[-1].default = True

    @store.bind(
        ui.PaginatedSelect(
            option_up=ui.SelectOption(
                label=gettext("item-lookup-ui-select-up-label"), value="$1", emoji="🔺"
            ),
            option_down=ui.SelectOption(
                label=gettext("item-lookup-ui-select-down-label"), value="$2", emoji="🔻"
            ),
            page=ui.PaginatedSelect.option_to_page_index(ctx.level_index, len(all_options)),
            all_options=all_options,
            placeholder=gettext("item-lookup-ui-select-placeholder"),
            custom_id=store.make_id(),
        )
    )
    async def level_select(inter: ui.MessageInteraction) -> None:
        assert inter.values
        value = inter.values[0]

        if level_select.update_on_own_option(value):
            return await inter.response.edit_message(components=layout)

        level_select.all_options[ctx.level_index].default = False
        ctx.level_index = int(value)
        level_select.all_options[ctx.level_index].default = True
        await respond(inter)

    @store.bind(
        ui.StringSelect(
            options=[
                ui.SelectOption(
                    label=gettext(f"tier-{stage.tier.name}").capitalize(),  # noqa: INT001
                    value=str(i),
                    emoji=EMOJIS.tiers[stage.tier],
                )
                for i, stage in enumerate(ctx.item.stages)
            ],
            custom_id=store.make_id(),
        )
    )
    async def tier_select(inter: ui.MessageInteraction) -> None:
        assert inter.values
        new_stage = int(inter.values[0])
        old_stage, ctx.stage_index = ctx.stage_index, new_stage
        new_options = ctx.get_level_options()

        if new_stage > old_stage:
            ctx.level_index = 0
            page = 0

        else:
            ctx.level_index = ctx.get_max_level()
            page = level_select.option_to_page_count(len(new_options)) - 1

        new_options[ctx.level_index].default = True
        level_select.set_all_options(new_options, page)

        tier_select.options[old_stage].default = False
        tier_select.options[new_stage].default = True
        await respond(inter)

    tier_select.options[ctx.stage_index].default = True

    layout = [[tier_select], [level_select], button_row]
    return layout  # noqa: RET504


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
            debug_footer(embed)

    layout = [[buffs_button]]
    return layout  # noqa: RET504 https://github.com/astral-sh/ruff/issues/14052
