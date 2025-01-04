from collections import abc
from functools import partial
from itertools import chain
from typing import Any, ClassVar

import attrs

from discord import ComponentLimits, EmbedColorType
from disnake import Embed, Locale
from disnake.utils import MISSING

from app import i18n
from app.assets import ASSETS, INVISIBLE_CHAR, get_weight_emoji
from app.bridges import ui
from app.bridges.all import embed_image
from app.devtools import debug_footer
from app.models import ItemPack, MechBuild, Player

from supermechs.all import ItemTypeName, Mech, abc as smabc, dominant_element, mech_summary
from supermechs.enums import ItemElementName, StatName


def embed_mech(mech: smabc.Mech[smabc.ItemData], locale: Locale, name: str) -> Embed:
    embed = Embed(
        title=i18n.get_message(locale, "mech-summary-title", name=name),
        color=color_from_mech(mech),
    ).add_field(i18n.get_message(locale, "mech-summary-field"), format_summary(mech, locale))
    return embed


def get_mech_config(mech: smabc.Mech[smabc.ItemData], /) -> str:
    """Return a string of IDs of items visible on image."""
    items = (mech.torso, mech.legs, mech.drone)
    items = chain(items, mech.side_weapons(), mech.top_weapons())
    return "_".join("0" if item is None else str(item.id) for item in items)


def format_summary(
    mech: Mech[smabc.HasStats], locale: Locale, buff_with: object | None = None
) -> str:
    """Return a string of lines formatted with mech stats.

    Parameters
    ----------
    mech:
        `Mech` to format stats of.
    locale:
        `Locale` to use for i18n of stat names.
    buff_with: optional
        `ArenaShop` to apply buffs from.
    """
    summary = mech_summary(mech)
    values = attrs.asdict(summary, recurse=False)
    del values[StatName.weight]

    # if buff_with is not None:

    parts = [
        f"{ASSETS.stats[StatName.weight]} **{summary.weight:.0f}**"
        f" {i18n.get_stat_name(locale, StatName.weight)}"
        f" {get_weight_emoji(int(summary.weight))}"
    ]

    parts.extend(
        f"{ASSETS.stats[stat].emoji} **{value:.0f}** {i18n.get_stat_name(locale, stat)}"
        for stat, value in values.items()
    )
    return "\n".join(parts)


def slot_emoji(slot: smabc.MechSlot, /) -> str:
    """Return the emoji representing a slot, with respect to the right & left variants."""
    if slot.startswith(("top", "side")):
        slot_name, _, index = slot.rpartition("_")
        asset = ASSETS.sided_types[slot_name]
        return (asset.right if int(index) % 2 else asset.left).emoji

    return ASSETS.types[slot].emoji


def sorted_options(
    options: abc.Mapping[smabc.ItemElement, list[ui.SelectOption]],
    primary_element: smabc.ItemElement | None,
    /,
) -> list[ui.SelectOption]:
    """Return a list of `SelectOption`s sorted by element.

    #### Note: this ignores the option limit.
    """
    all_options: list[ui.SelectOption] = []

    if sum(map(len, options.values())) + 1 <= ComponentLimits.select_options:
        it = options.values()

    else:
        element_order = [
            ItemElementName.PHYSICAL,
            ItemElementName.EXPLOSIVE,
            ItemElementName.ELECTRIC,
            "COMBINED",
        ]

        if primary_element is not None:
            element_order.remove(primary_element)
            element_order.insert(0, primary_element)

        it = (options[smabc.ItemElement(key)] for key in element_order)

    for option_list in it:
        all_options += option_list

    return all_options


def color_from_mech(mech: smabc.Mech[smabc.ItemData], /) -> EmbedColorType:
    element = dominant_element(mech)

    if element is None:
        if mech.torso is None:
            return None

        element = mech.torso.element

    return ASSETS.elements[element].color


def group_items(pack: ItemPack, /) -> dict[Type, dict[Element, list[ui.SelectOption]]]:
    item_groups = {type_: {element: list[ItemData]() for element in Element} for type_ in Type}

    for item in pack.items.values():
        item_groups[item.type][item.element].append(item)

    for element_dict in item_groups.values():
        for item_list in element_dict.values():
            item_list.sort(key=lambda item: item.name)

    return {
        type_: {
            element: [
                ui.SelectOption(
                    label=item.name, value=str(item.id), emoji=ASSETS.elements[item.element.name].emoji
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


class MechView:
    store: ui.CallbackStore
    mech: Mech[Item]
    pack: ItemPack
    arena_shop: ArenaShop
    embed: Embed
    locale: Locale
    paginator: ui.Paginator[abc.Sequence[abc.Sequence[ui.MessageUIComponent]]]
    active: ui.ToggleButton | None
    empty_option: ui.SelectOption
    mech_config: str

    command_mention: ClassVar[str] = "`/buffs`"

    # pages of rows of components
    LAYOUT: abc.Sequence[abc.Sequence[abc.Sequence[SlotType]]] = (
        (
            ((Type.TOP_WEAPON,  0), Type.DRONE, (Type.TOP_WEAPON,  1), Type.CHARGE),
            ((Type.SIDE_WEAPON, 2), Type.TORSO, (Type.SIDE_WEAPON, 3), Type.TELEPORTER),
            ((Type.SIDE_WEAPON, 0), Type.LEGS,  (Type.SIDE_WEAPON, 1), Type.HOOK),
        ),
        (
            tuple((Type.MODULE, n) for n in range(0, 4)),  # noqa: PIE808
            tuple((Type.MODULE, n) for n in range(4, 8)),
        ),
    )  # fmt: skip
    DUMMY_BUTTONS = tuple(
        ui.ActionButton(label=INVISIBLE_CHAR, disabled=True, custom_id=f"$dummy{n}")
        for n in range(4)
    )
    PAGE_EMOJI = (ASSETS.types[ItemTypeName.MODULE].emoji, ASSETS.types[ItemTypeName.TORSO].emoji)

    def __init__(
        self,
        store: ui.CallbackStore,
        build: MechBuild,
        pack: ItemPack,
        # renderer: PackRenderer,
        player: Player,
        locale: Locale,
    ) -> None:
        self.store = store
        self.mech = build.mech
        self.pack = pack
        self.renderer: Any = object()  # TODO
        self.arena_shop = player.arena_shop
        self.embed = embed_mech(build.mech, locale, build.name)
        self.locale = locale
        self.active = None
        self.empty_option = make_empty_option(locale)
        self.mech_config = get_mech_config(build.mech)
        self.item_groups = group_items(pack)
        self.init_pages(store)

    def init_pages(self, store: ui.CallbackStore) -> None:  # noqa: PLR0915
        gettext = i18n.get_gettext(self.locale)

        @store.bind(ui.ActionButton(emoji=self.PAGE_EMOJI[0], custom_id=store.make_id()))
        async def modules_button(inter: ui.MessageInteraction) -> None:
            """Swap mech view with modules viw and back."""
            self.paginator.index ^= 1  # 0 or 1
            modules_button.emoji = self.PAGE_EMOJI[self.paginator.index]
            await inter.response.edit_message(components=self.paginator.page)

        @store.bind(ui.ToggleButton(label="🡅", custom_id=store.make_id()))
        async def buffs_button(inter: ui.MessageInteraction) -> None:
            """Toggle arena buffs to mech's stats."""
            if is_shop_empty(self.arena_shop):
                return await inter.response.send_message(
                    gettext("mech-build-no-buffs", command_mention=self.command_mention),
                    ephemeral=True,
                )

            buffs_button.toggle()
            assert self.embed._fields is not None  # pyright: ignore[reportPrivateUsage]
            self.embed._fields[0]["value"] = format_summary(  # pyright: ignore[reportPrivateUsage]
                self.mech, self.locale, self.arena_shop if buffs_button.on else None
            )
            await inter.response.edit_message(embed=self.embed, components=self.paginator.page)

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
            """Item select dropdown."""
            assert self.active is not None
            assert inter.values is not None
            value = inter.values[0]

            if select.update_on_own_option(value):
                return await inter.response.edit_message(components=self.paginator.page)

            slot = self.id_to_slot[self.active.custom_id]

            if value == self.empty_option.value:
                item = None
                select.placeholder = None
                self.active.style_off = ui.ButtonStyle.gray

            else:
                item_data = self.pack.get_item(ItemID(value))
                target_type = slot[0] if isinstance(slot, tuple) else slot

                if item_data.type is not target_type:
                    # challenge complete: How Did We Get Here?
                    msg = f"{item_data.type} is not valid for slot {target_type}"
                    raise RuntimeWarning(msg)

                item = Item.maxed(item_data)
                select.placeholder = item_data.name
                self.active.style_off = ui.ButtonStyle.green

            self.mech[slot] = item
            self.embed.color = color_from_mech(self.mech)
            self.set_state_idle()

            self.embed.set_field_at(
                0,
                name="Stats:",
                value=format_summary(
                    self.mech,
                    self.locale,
                    self.arena_shop if buffs_button.on else None,
                ),
            )
            new_config = get_mech_config(self.mech)

            if new_config == self.mech_config:
                return await inter.response.edit_message(
                    embed=self.embed, components=self.paginator.page
                )

            self.mech_config = new_config
            url, file = None, MISSING

            if False:
                if self.mech.torso is not None:
                    image = self.renderer.create_mech_image(self.mech)
                    url, file = embed_image(image, new_config)

            self.embed.set_image(url)

            if __debug__:
                debug_footer(self.embed, replace=True)

            await inter.response.edit_message(
                embed=self.embed, file=file, components=self.paginator.page, attachments=[]
            )

        self.select = select
        id_to_slot: dict[str, SlotType] = {}

        async def slot_button_cb(button: ui.ToggleButton, inter: ui.MessageInteraction) -> None:
            if button.on:
                self.set_state_idle()

            elif self.active is not None:
                self.switch_active_button(button)

            else:
                self.set_state_active(button)

            await inter.response.edit_message(components=self.paginator.page)

        def make_button(slot: SlotType, /) -> ui.ToggleButton:
            btn = ui.ToggleButton(
                style_off=(
                    ui.ButtonStyle.gray if self.mech[slot] is None else ui.ButtonStyle.green
                ),
                style_on=ui.ButtonStyle.blurple,
                emoji=slot_emoji(slot),
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
        options = self.item_groups[slot[0] if isinstance(slot, tuple) else slot]
        element = dominant_element(self.mech)
        self.select.all_options = [self.empty_option, *sorted_options(options, element)]
        item = self.mech[slot]
        self.select.placeholder = self.empty_option.label if item is None else item.name
