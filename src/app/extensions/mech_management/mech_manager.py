# pyright: reportUninitializedInstanceVariable=false
import copy
from collections import Counter, abc
from functools import partial
from typing import Any, ClassVar, Protocol

from discord import ComponentLimits, EmbedColorType
from disnake import Embed, Locale
from disnake.utils import MISSING

from app import i18n, ui
from app.assets import COLORS, EMOJIS, get_slot_emoji
from app.devtools import debug_footer
from app.embed_utils import embed_image
from app.gamerules import ARENA_BONUSES
from app.managers import packs
from app.models import MechBuild, Player
from app.models.item import HasStats, Item
from app.text_utils import Char

import dupermechs.all as sm
from dupermechs import stats
from dupermechs.arenashop import bind_levels
from dupermechs.enums import ItemStat, MechSlot, MechStat

SLOT_TO_TYPE: abc.Mapping[sm.Mech.Slot, sm.Item.Type] = {
    sm.Mech.Slot.torso: sm.Item.Type.torso,
    sm.Mech.Slot.legs: sm.Item.Type.legs,
    sm.Mech.Slot.drone: sm.Item.Type.drone,
    sm.Mech.Slot.side_weapon_1: sm.Item.Type.side_weapon,
    sm.Mech.Slot.side_weapon_2: sm.Item.Type.side_weapon,
    sm.Mech.Slot.side_weapon_3: sm.Item.Type.side_weapon,
    sm.Mech.Slot.side_weapon_4: sm.Item.Type.side_weapon,
    sm.Mech.Slot.top_weapon_1: sm.Item.Type.top_weapon,
    sm.Mech.Slot.top_weapon_2: sm.Item.Type.top_weapon,
    sm.Mech.Slot.charge: sm.Item.Type.charge,
    sm.Mech.Slot.teleport: sm.Item.Type.teleport,
    sm.Mech.Slot.hook: sm.Item.Type.hook,
    sm.Mech.Slot.shield: sm.Item.Type.shield,
    sm.Mech.Slot.perk: sm.Item.Type.perk,
    sm.Mech.Slot.module_1: sm.Item.Type.module,
    sm.Mech.Slot.module_2: sm.Item.Type.module,
    sm.Mech.Slot.module_3: sm.Item.Type.module,
    sm.Mech.Slot.module_4: sm.Item.Type.module,
    sm.Mech.Slot.module_5: sm.Item.Type.module,
    sm.Mech.Slot.module_6: sm.Item.Type.module,
    sm.Mech.Slot.module_7: sm.Item.Type.module,
    sm.Mech.Slot.module_8: sm.Item.Type.module,
}


def embed_mech(
    build: MechBuild, locale: Locale, arena_buffs: sm.IArenaShopLevels | None = None
) -> Embed:
    summary = get_mech_stats(build.mech, arena_buffs)
    return Embed(
        title=i18n.get_message(
            locale, "mech-summary-title", name=build.name.unwrap_or("Unnamed Mech")
        ),
        color=color_from_mech(build.mech),
    ).add_field(
        i18n.get_message(locale, "mech-summary-field"),
        format_summary(summary, locale),
    )


class HasItemId(Protocol):
    @property
    def id(self) -> sm.Item.Id: ...


def get_mech_config(mech: sm.Mech[HasItemId], /) -> str:
    """Return a string of IDs of items visible on image."""
    items = (
        mech.torso, mech.legs, mech.drone,
        mech.side_weapon_1, mech.side_weapon_2, mech.side_weapon_4, mech.side_weapon_4,
        mech.top_weapon_1, mech.top_weapon_2,
    )  # fmt: skip
    return "_".join("0" if item is None else str(item.id) for item in items)


def iter_items[T](mech: sm.Mech[T], /) -> abc.Iterator[T]:
    for slot in sm.Mech.Slot:
        if (item := mech[slot]) is not None:
            yield item


def get_mech_stats(
    mech: sm.Mech[HasStats], arena_buffs: sm.IArenaShopLevels | None = None
) -> sm.ItemStats:
    mech_stats = stats.combine(item.stats for item in iter_items(mech))
    mech_stats_parts = [mech_stats]

    if arena_buffs is not None:
        buffs = bind_levels(arena_buffs, ARENA_BONUSES)
        mech_stats_parts.append(stats.bonus_mech_stats(mech_stats, buffs))

    return stats.combine(mech_stats_parts)


def format_summary(summary: sm.IItemStats, locale: Locale) -> str:
    """Return a string of lines formatted with mech stats."""
    overload = stats.overload_hp_penalty(summary.weight)  # TODO# safe_weight
    summary = copy.replace(summary, hit_points=summary.hit_points - overload)

    parts = [
        f"{EMOJIS.stats.weight} **{summary.weight}**"
        f" {i18n.get_stat_name(locale, MechStat.weight)}"
        f" {EMOJIS.get_weight_emoji(summary.weight)}"
    ]

    def add_part(value: int, emoji: str, stat: ItemStat) -> None:
        if value != 0:
            parts.append(f"{emoji} **{value}** {i18n.get_stat_name(locale, stat)}")

    if overload:
        parts.append(
            f"{EMOJIS.stats.hit_points} **{summary.hit_points}**"
            f" {i18n.get_stat_name(locale, MechStat.hit_points)}"
            f" ***{-overload}*** {EMOJIS.stats.weight}"
        )

    else:
        add_part(summary.hit_points, EMOJIS.stats.hit_points, ItemStat.hit_points)

    # fmt: off
    add_part(summary.energy_capacity, EMOJIS.stats.energy_capacity, ItemStat.energy_capacity)
    add_part(summary.energy_regeneration, EMOJIS.stats.energy_regeneration, ItemStat.energy_regeneration)
    add_part(summary.heat_capacity, EMOJIS.stats.heat_capacity, ItemStat.heat_capacity)
    add_part(summary.heat_cooling, EMOJIS.stats.heat_cooling, ItemStat.heat_cooling)
    add_part(summary.physical_resistance, EMOJIS.stats.physical_resistance, ItemStat.physical_resistance)
    add_part(summary.explosive_resistance, EMOJIS.stats.explosive_resistance, ItemStat.explosive_resistance)
    add_part(summary.electric_resistance, EMOJIS.stats.electric_resistance, ItemStat.electric_resistance)
    add_part(summary.bullets_capacity, EMOJIS.stats.bullets_capacity, ItemStat.bullets_capacity)
    add_part(summary.rockets_capacity, EMOJIS.stats.rockets_capacity, ItemStat.rockets_capacity)
    add_part(summary.walk, EMOJIS.stats.walk, ItemStat.walk)
    add_part(summary.jump, EMOJIS.stats.jump, ItemStat.jump)
    # fmt: on
    return "\n".join(parts)


def sorted_options(
    options: abc.Mapping[sm.Item.Element, abc.Sequence[ui.SelectOption]],
    primary_element: sm.Item.Element | None,
) -> list[ui.SelectOption]:
    """Return a list of `SelectOption`s sorted by element.

    #### Note: this ignores the option limit.
    """
    all_options: list[ui.SelectOption] = []

    if sum(map(len, options.values())) + 1 <= ComponentLimits.select_options:
        it = options.values()

    else:
        element_order = [
            sm.Item.Element.physical,
            sm.Item.Element.explosive,
            sm.Item.Element.electric,
            sm.Item.Element.combined,
            sm.Item.Element.other,
        ]

        if primary_element is not None:
            element_order.remove(primary_element)
            element_order.insert(0, primary_element)

        it = (options[key] for key in element_order)

    for option_list in it:
        all_options += option_list

    return all_options


class HasElement(Protocol):
    @property
    def element(self) -> sm.Item.Element: ...


def dominant_element(mech: sm.Mech[HasElement], /, threshold: int = 2) -> sm.Item.Element | None:
    counter = Counter[sm.Item.Element]()

    def add(item: HasElement | None, /) -> None:
        if item is not None:
            counter[item.element] += 1

    add(mech.torso)
    add(mech.legs)
    add(mech.drone)
    add(mech.hook)
    add(mech.side_weapon_1)
    add(mech.side_weapon_2)
    add(mech.side_weapon_3)
    add(mech.side_weapon_4)
    add(mech.top_weapon_1)
    add(mech.top_weapon_2)

    match counter.most_common(2):
        case [(element, _)]:
            return element

        case [(element, count_1), (_, count_2)] if count_1 - count_2 >= threshold:
            return element

        case _:
            return None


def color_from_mech(mech: sm.Mech[HasElement], /) -> EmbedColorType:
    element = dominant_element(mech)

    if element is None:
        if mech.torso is None:
            return None

        element = mech.torso.element

    return COLORS.elements[element]


def group_items() -> dict[sm.Item.Type, dict[sm.Item.Element, list[ui.SelectOption]]]:
    item_groups = {
        type_: {element: list[sm.IItem]() for element in sm.Item.Element} for type_ in sm.Item.Type
    }

    for item in packs.iter_items():
        item_groups[item.type][item.element].append(item)

    for element_dict in item_groups.values():
        for item_list in element_dict.values():
            item_list.sort(key=lambda item: item.name)

    return {
        type_: {
            element: [
                ui.SelectOption(
                    label=item.name,
                    value=str(item.id),
                    emoji=EMOJIS.elements[item.element],
                )
                for item in items
            ]
            for element, items in element_dict.items()
        }
        for type_, element_dict in item_groups.items()
    }


def make_empty_option(locale: Locale, /) -> ui.SelectOption:
    return ui.SelectOption(
        label=i18n.get_message(locale, "ui-empty-option-label"),
        description=i18n.get_message(locale, "ui-empty-option-desc"),
        value="$empty",
        emoji="⏏",
    )


def is_shop_empty(shop: sm.IArenaShopLevels, /) -> bool:
    return all(shop[c] == 0 for c in sm.ArenaShop.Category)


class MechView:
    store: ui.CallbackStore
    build: MechBuild
    arena_shop: sm.IArenaShopLevels
    locale: Locale
    paginator: ui.Paginator[abc.Sequence[abc.Sequence[ui.MessageUIComponent]]]
    active: ui.ToggleButton | None
    empty_option: ui.SelectOption
    mech_config: str

    buffs_mention: ClassVar[str] = "`/buffs`"

    # pages of rows of components
    LAYOUT: abc.Sequence[abc.Sequence[abc.Sequence[MechSlot]]] = (
        (
            (MechSlot.top_weapon_1, MechSlot.drone, MechSlot.top_weapon_2, MechSlot.charge),
            (MechSlot.side_weapon_3, MechSlot.torso, MechSlot.side_weapon_4, MechSlot.teleport),
            (MechSlot.side_weapon_1, MechSlot.legs, MechSlot.side_weapon_2, MechSlot.hook),
        ),
        (
            (MechSlot.module_1, MechSlot.module_2, MechSlot.module_3, MechSlot.module_4),
            (MechSlot.module_5, MechSlot.module_6, MechSlot.module_7, MechSlot.module_8),
        ),
    )  # fmt: skip
    DUMMY_BUTTONS = tuple(
        ui.ActionButton(label=Char.BLANK, disabled=True, custom_id=f"$dummy{n}") for n in range(4)
    )
    PAGE_EMOJI = (EMOJIS.types.module, EMOJIS.types.torso)

    def __init__(
        self,
        store: ui.CallbackStore,
        build: MechBuild,
        player: Player,
        locale: Locale,
    ) -> None:
        self.store = store
        self.build = build
        self.renderer: Any = object()  # TODO
        self.arena_shop = player.arena_shop
        self.locale = locale
        self.active = None
        self.empty_option = make_empty_option(locale)
        self.mech_config = get_mech_config(build.mech)
        self.item_groups = group_items()
        self.init_pages(store)

    def init_pages(self, store: ui.CallbackStore) -> None:
        gettext = i18n.get_gettext(self.locale)

        @store.bind(ui.ActionButton(emoji=self.PAGE_EMOJI[0], custom_id=store.make_id()))
        async def modules_button(inter: ui.MessageInteraction) -> None:
            self.paginator.index ^= 1  # 0 or 1
            modules_button.emoji = self.PAGE_EMOJI[self.paginator.index]
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(ui.ToggleButton(label="🡅", custom_id=store.make_id()))
        async def buffs_button(inter: ui.MessageInteraction) -> None:
            if is_shop_empty(self.arena_shop):
                return await inter.response.send_message(
                    gettext("mech-build-no-buffs", command_mention=self.buffs_mention),
                    ephemeral=True,
                )

            buffs_button.toggle()
            embed = embed_mech(
                self.build, self.locale, self.arena_shop if buffs_button.on else None
            )
            await inter.response.edit_message(embed=embed, components=self.paginator.page)

        @store.bind(
            ui.ActionButton(
                label=gettext("ui-quit"), style=ui.ButtonStyle.red, custom_id=store.make_id()
            )
        )
        async def quit_button(inter: ui.MessageInteraction) -> None:
            store.stop()
            await inter.response.defer(ephemeral=True)

        @store.bind(
            ui.PaginatedSelect(
                option_up=ui.SelectOption(
                    label=gettext("mech-build-ui-select-up-label"),
                    value="$up",
                    emoji="🔺",
                    description=gettext("mech-build-ui-select-up-desc"),
                ),
                option_down=ui.SelectOption(
                    label=gettext("mech-build-ui-select-down-label"),
                    value="$down",
                    emoji="🔻",
                    description=gettext("mech-build-ui-select-down-desc"),
                ),
                placeholder=gettext("mech-build-ui-select-placeholder"),
                all_options=[ui.SelectOption(label="$")],  # 1 option required even when disabled
                disabled=True,
                custom_id=store.make_id(),
            )
        )
        async def select(inter: ui.MessageInteraction) -> None:
            assert self.active is not None
            assert inter.values
            value = inter.values[0]

            if select.update_on_own_option(value):
                return await inter.response.edit_message(components=self.paginator.page)

            slot = self.id_to_slot[self.active.custom_id]

            if value == self.empty_option.value:
                item = None
                select.placeholder = None
                self.active.style_off = ui.ButtonStyle.gray

            else:
                sm_item = packs.get_item_by_id(sm.Item.Id(int(value)))
                item = Item.maxed(sm_item)

                select.placeholder = item.name
                self.active.style_off = ui.ButtonStyle.green

            self.build.mech = copy.replace(self.build.mech, **{slot.name: item})
            self.set_state_idle()

            embed = embed_mech(
                self.build, self.locale, self.arena_shop if buffs_button.on else None
            )
            new_config = get_mech_config(self.build.mech)

            if new_config == self.mech_config:
                return await inter.response.edit_message(
                    embed=embed, components=self.paginator.page
                )

            self.mech_config = new_config
            url, file = None, MISSING

            if False:  # FIXME: mech image rendering
                if self.build.mech.torso is not None:
                    image = self.renderer.create_mech_image(self.build.mech)
                    url, file = embed_image(image, new_config)

            embed.set_image(url)

            if __debug__:
                debug_footer(embed, replace=True)

            await inter.response.edit_message(
                embed=embed, file=file, components=self.paginator.page, attachments=[]
            )

        self.select = select
        id_to_slot: dict[str, MechSlot] = {}

        async def slot_button_cb(button: ui.ToggleButton, inter: ui.MessageInteraction) -> None:
            if button.on:
                self.set_state_idle()

            elif self.active is not None:
                self.switch_active_button(button)

            else:
                self.set_state_active(button)

            await inter.response.edit_message(components=self.paginator.page)

        def make_button(slot: MechSlot, /) -> ui.ToggleButton:
            btn = ui.ToggleButton(
                style_off=(
                    ui.ButtonStyle.gray if self.build.mech[slot] is None else ui.ButtonStyle.green
                ),
                style_on=ui.ButtonStyle.blurple,
                emoji=get_slot_emoji(slot),
                custom_id=self.store.make_id(),
            )
            id_to_slot[btn.custom_id] = slot
            self.store.bind(btn)(partial(slot_button_cb, btn))
            return btn

        self.paginator = ui.Paginator(
            (
                [
                    [*map(make_button, self.LAYOUT[0][0]), modules_button],
                    [*map(make_button, self.LAYOUT[0][1]), buffs_button],
                    [*map(make_button, self.LAYOUT[0][2]), quit_button],
                    [select],
                ],
                [
                    [*map(make_button, self.LAYOUT[1][0]), modules_button],
                    [*map(make_button, self.LAYOUT[1][1]), buffs_button],
                    [*self.DUMMY_BUTTONS, quit_button],
                    [select],
                ],
            )
        )
        self.id_to_slot = id_to_slot

    def set_state_idle(self) -> None:
        if self.active is not None:
            self.active.on = False
            self.active = None
        self.select.disabled = True

    def set_state_active(self, button: ui.ToggleButton, /) -> None:
        button.on = True
        self.active = button
        self.select.disabled = False
        self.update_dropdown(button)

    def switch_active_button(self, button: ui.ToggleButton, /) -> None:
        assert self.active is not None
        self.active.on = False
        button.on = True
        self.active = button
        self.update_dropdown(button)

    def update_dropdown(self, button: ui.ToggleButton, /) -> None:
        slot = self.id_to_slot[button.custom_id]
        type = SLOT_TO_TYPE[slot]
        options = self.item_groups[type]
        element = dominant_element(self.build.mech)
        self.select.set_all_options([self.empty_option, *sorted_options(options, element)])
        item = self.build.mech[slot]
        self.select.placeholder = self.empty_option.label if item is None else item.name
